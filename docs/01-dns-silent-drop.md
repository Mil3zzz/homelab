# DNS queries dropped with no log entry anywhere

**Symptom:** A resolver I'd just built answered queries fine from its own console and was totally unreachable from any other VLAN. No error worth reading, no rejection — just a timeout. Firewall logs showed nothing at all, not even an attempt.

---

## Setup

I'd stood up a second DNS resolver on its own hardware to get rid of a single point of failure. Pi-hole and Unbound were both installed and working — confirmed locally. The resolver sat on the servers VLAN, and I was testing from a workstation on the clients VLAN.

Locally, on the resolver:

```
nslookup github.com 127.0.0.1
→ resolves fine
```

From another VLAN:

```
nslookup github.com <resolver-ip>
→ DNS request timed out
```

## What I ruled out

**Host firewall first**, since it's a thirty-second check. `ufw status` came back inactive. Not that.

**Was the service actually listening on the network, or just loopback?**

```
ss -lntup | grep :53
```

Bound to `0.0.0.0:53`, both TCP and UDP. Listening on everything, not just localhost — so that wasn't it either.

**Routing.** Ping from the workstation to the resolver: clean, sub-millisecond. Ping from the firewall itself, sourced from the right VLAN interface: also clean. Traffic was clearly making it across the boundary.

**Firewall rules.** Built an explicit pass rule, TCP/UDP, source the clients VLAN, destination the resolver, port 53. Applied it. Nothing changed.

**The live log, with a query actively in flight.** This is the part that actually reframed things for me. Nothing showed up. Not a pass line, not a block line. Nothing.

## What that actually meant

An empty log isn't nothing — it's information about who made the decision. A firewall logs what it evaluates. If a packet never produces a log line on either side, either it never got to the firewall, or it got past the firewall fine and the *destination* just didn't answer.

I'd already proven routing worked both directions, and ICMP to the same host was fine too, which meant the host was up and actively handling traffic. So the gap between "ping works" and "DNS doesn't" on a host that's demonstrably listening on port 53 isn't a network issue. That's the application choosing not to respond.

That's what moved me off the network stack and into Pi-hole's own config.

## Root cause

Pi-hole has a setting called `listeningMode` that decides which source networks it'll actually answer — completely separate from what interface it's bound to, and separate from any firewall entirely.

```
pihole-FTL --config dns.listeningMode
→ LOCAL
```

`LOCAL` means: only answer queries from my own subnet. Anything else gets dropped, not rejected — just discarded. No log entry either side, because nothing actually refused the packet. It just got ignored.

## Fix

```
pihole-FTL --config dns.listeningMode ALL
systemctl restart pihole-FTL
```

Worked immediately from the other VLAN.

## What I took from it

Confirming a service is "listening" doesn't mean it'll answer *you*. `ss` told me it was bound everywhere, and I read that as proof the app layer was fine — but binding and access control aren't the same thing, and I'd been treating them as one.

An empty firewall log isn't a dead end, it's a clue. I wasted time assuming the logs just weren't showing me enough. They were showing me exactly what I needed — that the firewall wasn't the thing making the call.

Testing one protocol against another on the same host is a fast way to isolate the layer. ICMP working while DNS failed, to a host I'd already confirmed had port 53 open, is basically pointing at the application before you even know why.

I ran into a nearly identical shape of problem later — a container unreachable on the right subnet, no logs anywhere, network side all checked out — and got there in a few minutes instead of most of an evening. Different actual cause (missing VLAN tag on the interface, this time), but the same pattern: a config layer somewhere that drops traffic without ever writing it down.
