#!/usr/bin/env python3
import subprocess
import time
import os
import re

SWITCHES = ["s1", "s2", "s3"]
REFRESH_SECONDS = 5

def run_cmd(cmd):
    try:
        out = subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL, text=True)
        return out.strip()
    except subprocess.CalledProcessError:
        return ""

def parse_flows(raw):
    flows = []
    for line in raw.splitlines():
        line = line.strip()
        if not line or "NXST_FLOW reply" in line:
            continue

        pkt_match = re.search(r"n_packets=(\d+)", line)
        prio_match = re.search(r"priority=(\d+)", line)
        actions_match = re.search(r"actions=([^,]+.*)$", line)

        packets = int(pkt_match.group(1)) if pkt_match else 0
        priority = int(prio_match.group(1)) if prio_match else 0
        actions = actions_match.group(1).strip() if actions_match else "NONE"

        status = "ACTIVE ✓" if packets > 0 else "IDLE"

        # Compact rule preview
        rule = line
        if len(rule) > 90:
            rule = rule[:87] + "..."

        flows.append({
            "priority": priority,
            "packets": packets,
            "status": status,
            "rule": rule,
            "actions": actions
        })

    flows.sort(key=lambda x: (-x["priority"], -x["packets"]))
    return flows

def print_header():
    print("+--------------------------------------------------+")
    print("|              Multi-Switch Flow Table Analyzer    |")
    print("+--------------------------------------------------+\n")

def print_switch_table(sw, flows):
    print("=" * 52)
    print(f" Switch: {sw}")
    print("=" * 52)
    print(f"{'Priority':<10} {'Packets':<9} {'Status':<10} Rule")
    print("-" * 90)

    if not flows:
        print(f"{'-':<10} {'-':<9} {'NO DATA':<10} No flow entries found")
    else:
        for f in flows[:8]:  # show top 8 entries
            print(f"{f['priority']:<10} {f['packets']:<9} {f['status']:<10} {f['rule']}")
    print()

def main():
    while True:
        os.system("clear")
        print_header()

        for sw in SWITCHES:
            raw = run_cmd(f"sudo ovs-ofctl -O OpenFlow10 dump-flows {sw}")
            flows = parse_flows(raw)
            print_switch_table(sw, flows)

        print(f"Refreshing every {REFRESH_SECONDS}s - Ctrl+C to stop")
        time.sleep(REFRESH_SECONDS)

if __name__ == "__main__":
    main()
