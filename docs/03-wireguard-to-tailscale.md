# WireGuard: handshake completing, traffic going nowhere

**Symptom:** First, a client that just sent packets forever with zero received and no handshake at all. Once that got fixed, the handshake worked and real data moved — but nothing actually routed anywhere. Eventually replaced the whole thing with Tailscale, and not as a consolation prize.

---

## What I actually wanted

Remote access from my phone on cellular, with two real requirements:

1. Reach internal stuff — the SIEM dashboard, the hypervisor, the domain controller — without putting any of it on the public internet. A domain controller reachable from outside is a much worse tradeoff than whatever convenience it saves.
2. Route all traffic through home so DNS filtering still applies while I'm out. That means a full tunnel, not split.

## First problem: no handshake, period

The client showed data sent climbing forever, zero received, no handshake timestamp ever. Tried both a DDNS hostname and the raw public IP directly — identical failure either way, which immediately ruled out DNS/DDNS propagation as the cause.

Checked, in order:

**Was the peer actually attached to the server instance?** In OPNsense, generating a peer doesn't automatically attach it to the running instance — you have to select it separately. Confirmed it was checked and saved.

**Firewall rule on WAN.** Confirmed a pass rule existed for UDP/51820 to the WAN address. Found I'd accidentally created it twice — deleted the duplicate.

**Server-side status.** The WireGuard status page showed zero packets sent or received, ever. The server had literally never seen a single packet from my phone.

That last one changed everything. If the firewall rule is genuinely correct and the daemon still hasn't seen one packet, the packet isn't even arriving — meaning the problem is upstream of the firewall entirely, not inside it.

### Double NAT

The firewall's WAN interface had a *private* IP address. My ISP's gateway was sitting in router mode, holding the actual public IP, and handing the firewall a private address on its own internal network.

So inbound UDP on 51820 was hitting the ISP's gateway first, which had no idea what to do with it, and just dropping it there.

I checked whether this was CGNAT — which would've been a dead end entirely — by comparing what the ISP gateway itself reported as its WAN address against what an external IP checker showed from something behind it. They matched, so I did have a real public IP, it just wasn't landing directly on my firewall.

Fix: a port forward on the ISP gateway, UDP/51820 to the firewall's WAN address. Bridge mode would've actually solved the double NAT for good instead of just punching one hole through it, but the forward got me to a testable state faster.

### The endpoint

With the forward in place — still nothing. Turned out the phone's **Endpoint** field had the firewall's *internal* WAN address in it, the private one from the ISP's own subnet, not the public one.

My phone on cellular has zero route to a private address sitting inside my house. It had been sending handshake attempts into nothing this whole time.

Fixed the endpoint to the actual public IP with the port attached. Handshake completed immediately, and the status page started showing a live peer with real bytes moving both ways.

## Second problem: tunnel's up, nothing loads

Handshake confirmed, real data flowing. And no website would load at all.

Checked the outbound NAT rule — existed, correct subnet, translating to the WAN interface, mode set to hybrid so manual rules apply alongside the automatic ones. Checked the firewall rule on the tunnel interface itself — a pass rule allowing that subnet to reach anywhere. Both looked right.

Traffic still wasn't routing.

## Why I stopped here

At that point I was just toggling settings and re-testing without anything actually telling me where to look next. Every check kept coming back "this looks fine," which meant I'd run out of signal to follow — and at that point continuing just risks piling up half-changed config that becomes its own separate problem later.

Honestly, I'd already spent hours getting a full-tunnel VPN working through a double-NAT setup I don't fully control on the ISP side, and whatever was left was somewhere in the interaction between NAT, routing, and the tunnel interface. Solvable, probably, but not obviously the best use of more time when the actual goal was reachable a different way.

## Switching to Tailscale

Tailscale is WireGuard under the hood, minus the exact stuff I'd been fighting. Every node connects *outbound* to a coordination service, so NAT traversal just happens — no inbound port forwarding needed anywhere, which means the double NAT stops being a problem instead of something to work around.

What I actually did:

Installed the plugin on the firewall, authenticated the node. Advertised my internal subnets as routes, then had to separately approve them in the admin console — advertising alone doesn't turn them on, that cost me a few confused minutes. Then enabled the firewall as an exit node, approved that too, and selected it on the phone. Routes and exit node are two completely separate settings — routes get you to specific internal networks, exit node is what sends *everything* through home.

Confirmed it worked by reaching internal hosts from cellular, and separately checking an external IP lookup from the phone — it showed my home's public IP, not my carrier's, which meant full-tunnel egress was genuinely working and DNS filtering was coming along with it.

## What I took from it

Zero packets on the server side is a routing question, not a rules question. If nothing arrived, firewall rules are irrelevant — they only matter for packets that actually show up. I spent real time auditing rules that were never going to be the answer.

Check the topology before optimizing inside it. The double NAT was visible in about thirty seconds just by looking at the WAN address. I found it after already checking peer bindings, firewall rules, and rule ordering — all of which were downstream of a problem that made them beside the point.

Switching tools isn't giving up, sometimes it's the actual right call. I could've kept grinding on the routing. But the requirement was secure remote access with DNS filtering, not specifically "self-managed WireGuard, no matter what." Tailscale got me there in under an hour and removed a whole category of future breakage — the port forward, the DDNS dependency, anything that breaks the moment my ISP reassigns an address.

None of the earlier debugging was wasted, either. The endpoint mistake and the double NAT were both real problems that would've broken any inbound-port-based VPN regardless of which one I picked. Understanding why Tailscale's outbound-first model sidesteps both is exactly why I'd reach for it on purpose next time, not just because WireGuard didn't work out.
