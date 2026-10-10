# Mistakes and lessons

A lab where nothing goes wrong is a lab where you didn't learn much. This is the stuff I actually got wrong, dumb mistakes included.

---

## Design mistakes

### Putting the file share on the domain controller

I put a shared folder on the DC because it was already running and already had file sharing set up — pure convenience, not a decision. A capacity check later showed about **17 GB free** on its system drive, nowhere near enough for a semester of coursework on top of what AD itself and Windows updates need.

A domain controller running out of disk space doesn't fail gracefully. It takes authentication down for the whole domain.

Moved the share to a dedicated box with way more headroom. The real lesson isn't really "check free space first" — it's that a domain controller has exactly one job, and piling unrelated stuff onto core infrastructure because it happened to be convenient is exactly how a small oversight becomes a domain-wide outage.

### Almost building "redundancy" that wasn't

When I first planned a second DNS resolver, my instinct was to just run it as another container on the same hypervisor as the first one.

That protects against a process crashing and basically nothing else. Same power supply, same disk, same kernel, same physical box. Any of those failing takes out both "redundant" resolvers at the same time.

Put the second one on actual separate hardware instead. Redundancy means an independent failure path, not a second copy of the same thing sitting next to the first.

### Assuming everything needed to be public-facing

My original plan was to shove everything behind a reverse proxy and expose it to the internet. That was the default because it's what I'd seen other people do, not because I'd actually thought it through.

A domain controller or a SIEM dashboard reachable from the open internet is a much worse tradeoff than whatever convenience it saves — especially the SIEM, considering its entire job is watching for signs of compromise.

Now internal admin stuff is only reachable over the VPN. Anything public-facing is a deliberate choice with an actual reason behind it, not a default.

---

## Configuration mistakes

### Not clicking Apply

OPNsense (and a lot of switch UIs) stage changes and need an explicit apply step. I've burned time more than once debugging why a rule "wasn't working" when it had genuinely never been committed in the first place.

More than once. This one's fully on me, no interesting root cause to point to.

### Setting a VPN endpoint to an internal address

Set a phone's VPN config to use the firewall's *private* WAN address as the endpoint. A phone on cellular has no route to a private address sitting inside my house — obviously, in retrospect.

The actual tell was that it kept sending packets forever and getting nothing back, but I went and checked peer keys, firewall rules, and rule ordering before I checked the one field that literally decides where the packets are even being sent.

### Setting an access port to tagged instead of untagged

Briefly set up a switch port for a laptop as a tagged trunk member instead of a normal untagged access port. End devices don't speak VLAN tagging — they send plain untagged frames and expect the same back. Tagged ports are for links between switches/firewalls that need to carry multiple VLANs at once.

Related mistake: VLAN membership and PVID are two separate settings on these switches, not one. Set membership without matching the PVID, and untagged frames coming in still get classified into whatever VLAN the PVID points at — usually the default one, which is almost never where you actually wanted them.

### Deploying a container with no VLAN tag on a trunked bridge

Had an LXC container come up with the right IP address and zero connectivity — "destination host unreachable," from its own address, trying to reach its own gateway.

The bridge is a trunk carrying several tagged VLANs. With no tag set on the container, it was sitting on the native/untagged VLAN, not the one its IP actually belonged to. Correct on paper, wrong network in reality.

---

## Operational mistakes

### Three different passwords, none of them labeled

Separate credentials for the workstation login, SSH on the server, and the Samba share itself — Samba keeps its own password database completely separate from the system account. I kept typing the wrong one into the wrong prompt, and at one point ran several commands against the wrong machine entirely without noticing the hostname sitting right there in the prompt.

Fix was pretty simple in hindsight: label credentials by what they're actually for, not just by which host they belong to. And read the prompt before typing anything.

### A password I couldn't reproduce

Locked myself out of a fresh Linux install twice because I'd written down a generated password wrong. Both times the account had zero data on it, so reinstalling was genuinely faster than trying to recover it — but the actual failure was in how I was recording passwords in the first place, not bad luck.

There was also a stretch where a domain account turned out to have no sudo rights at all on the machine I was trying to administer, which I only figured out after several increasingly confusing failed attempts.

### Reinstalling without checking encryption first

My laptop's first install had no full-disk encryption at all. Didn't notice until I actually sat down and thought through what happens if the thing gets stolen — and realized deleting a domain account stops someone from *logging in*, it does nothing about someone just reading the disk directly.

Reinstalled with LUKS this time. Encryption is what actually addresses that specific risk; account management doesn't touch it.

---

## Patterns worth generalizing

When every layer checks out clean, the problem's in a layer you haven't looked at yet. I've now hit this exact shape twice — traffic silently dropped by some application setting with zero log trace anywhere, while firewall rules, routing, and interfaces were all genuinely correct and verified. An empty log isn't nothing, it's telling you something about which component actually made the call.

Test the layer underneath whatever's failing. A failed graphical login and a failed `kinit` are the same underlying problem, but the second one rules out the entire desktop stack in a single command.

Check the topology before optimizing inside it. I spent a while auditing firewall rules before I noticed my own firewall's WAN interface had a private IP address. Everything I'd checked up to that point was downstream of a fact that made all of it beside the point.

Deciding to switch tools is a real engineering decision, not a failure. Moving off self-managed WireGuard to Tailscale wasn't giving up on a hard problem — it was recognizing the actual requirement was secure remote access, not "WireGuard specifically, no matter what," and that a design with no inbound port dependency would just be less fragile long-term.
