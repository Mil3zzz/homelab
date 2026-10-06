#!/usr/bin/env python3
"""Daily Wazuh digest: summarise the last 24h of alerts and send them to the
kuma-alert-ai Cloudflare Worker, which asks Workers AI for a plain-English
digest and posts it to Discord. Only rule summaries leave this machine:
never raw log lines."""
import collections, datetime, gzip, json, os, sys, urllib.request

ALERTS_DIR = os.environ.get("WAZUH_ALERTS_DIR", "/var/ossec/logs/alerts")
KEY_FILE = os.environ.get("DIGEST_KEY_FILE", "/root/.wazuh-digest-key")
WORKER = os.environ.get("DIGEST_WORKER_URL",
                        "https://<your-worker>.workers.dev/wazuh")
HOURS = 24


def candidate_files():
    yday = datetime.datetime.now() - datetime.timedelta(days=1)
    base = os.path.join(ALERTS_DIR, yday.strftime("%Y"), yday.strftime("%b"),
                        "ossec-alerts-" + yday.strftime("%d"))
    return [base + ".json.gz", base + ".json", os.path.join(ALERTS_DIR, "alerts.json")]


def parse_time(ts):
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.datetime.strptime(ts, fmt)
        except (ValueError, TypeError):
            pass
    return None


def main():
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=HOURS)
    rules = collections.Counter()
    agents = collections.defaultdict(set)
    groups = {}
    levels = collections.Counter()
    total = 0
    read_any = False

    for path in candidate_files():
        if not os.path.exists(path):
            continue
        opener = gzip.open if path.endswith(".gz") else open
        with opener(path, "rt", errors="replace") as fh:
            read_any = True
            for line in fh:
                try:
                    a = json.loads(line)
                except ValueError:
                    continue
                t = parse_time(a.get("timestamp"))
                if t is None or t < cutoff:
                    continue
                rule = a.get("rule", {})
                level = int(rule.get("level", 0))
                key = (level, str(rule.get("id", "?")), rule.get("description", "?"))
                rules[key] += 1
                agents[key].add(a.get("agent", {}).get("name", "?"))
                groups[key] = rule.get("groups", [])[:3]
                levels[level] += 1
                total += 1

    if not read_any:
        sys.exit("No Wazuh alert files found in " + ALERTS_DIR)

    top = sorted(rules.items(), key=lambda kv: (-kv[0][0], -kv[1]))[:20]
    payload = {
        "hours": HOURS,
        "total": total,
        "highest_level": max(levels) if levels else 0,
        "by_level": {str(k): v for k, v in sorted(levels.items(), reverse=True)},
        "top": [
            {"level": k[0], "rule_id": k[1], "description": k[2], "count": n,
             "agents": sorted(agents[k])[:5], "groups": groups[k]}
            for k, n in top
        ],
    }

    with open(KEY_FILE) as fh:
        key = fh.read().strip()
    req = urllib.request.Request(
        WORKER + "?key=" + key,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "wazuh-digest/1.0"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        print("Sent digest of", total, "alerts:", resp.status, resp.read().decode()[:100])


if __name__ == "__main__":
    main()
