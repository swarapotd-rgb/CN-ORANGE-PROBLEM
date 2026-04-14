from pox.core import core
import pox.openflow.libopenflow_01 as of

log = core.getLogger()
mac_to_port = {}

BLOCK_SRC = "00:00:00:00:00:01"  # h1
BLOCK_DST = "00:00:00:00:00:03"  # h3


def add_flow(connection, match, actions, priority=10, idle=30, hard=120):
    msg = of.ofp_flow_mod()
    msg.match = match
    msg.priority = priority
    msg.idle_timeout = idle
    msg.hard_timeout = hard
    for a in actions:
        msg.actions.append(a)
    connection.send(msg)


def _handle_ConnectionUp(event):
    log.info("Switch %s connected", event.dpid)

    # Table-miss-like behavior: let PacketIn happen (POX handles PacketIn by default for misses)

    # Install high-priority DROP rule for h1 -> h3
    m = of.ofp_match(dl_src=BLOCK_SRC, dl_dst=BLOCK_DST)
    add_flow(event.connection, m, actions=[], priority=100, idle=0, hard=0)
    log.info("Installed block rule: %s -> %s on switch %s", BLOCK_SRC, BLOCK_DST, event.dpid)


def _handle_PacketIn(event):
    packet = event.parsed
    if not packet.parsed:
        return

    dpid = event.connection.dpid
    in_port = event.port

    src = str(packet.src)
    dst = str(packet.dst)

    if dpid not in mac_to_port:
        mac_to_port[dpid] = {}

    # Learn source MAC
    mac_to_port[dpid][src] = in_port

    # Block policy in PacketIn path too
    if src == BLOCK_SRC and dst == BLOCK_DST:
        log.info("Blocked packet: %s -> %s on switch %s", src, dst, dpid)
        return

    # Decide output port
    if dst in mac_to_port[dpid]:
        out_port = mac_to_port[dpid][dst]
        # Install learned forwarding flow
        m = of.ofp_match.from_packet(packet, in_port)
        add_flow(event.connection, m, [of.ofp_action_output(port=out_port)], priority=10)
    else:
        out_port = of.OFPP_FLOOD

    # Send packet out
    po = of.ofp_packet_out(data=event.ofp)
    po.actions.append(of.ofp_action_output(port=out_port))
    po.in_port = in_port
    event.connection.send(po)


def launch():
    core.openflow.addListenerByName("ConnectionUp", _handle_ConnectionUp)
    core.openflow.addListenerByName("PacketIn", _handle_PacketIn)
    log.info("Orange POX controller started")
