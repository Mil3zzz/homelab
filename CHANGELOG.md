# Changelog

What changed in the lab, newest first. Dates are when the work was done where I know the day, otherwise when it was written up here. Every commit in this repo is also timestamped: the **History** button on any file shows exactly when each line changed.

---

## 2026-10-10 (evening)
- Recovered the DNS/SIEM box after it booted without its USB backup drive and dropped into emergency mode. Added `nofail` to the drive's mount line so a missing drive can't block boot again ([write-up](docs/04-missing-mount-emergency-mode.md)).
- Cable cleanup in the rack: power and network separated, zip-tied loosely through the floor slots, nothing re-patched to a different switch port. Wrote a shutdown runbook of what can be unplugged and what needs a clean shutdown first.
- Added DHCP reservations in OPNsense for the services that matter (Pi, NAS, desktop, Open WebUI, Termix, monitoring, Immich host) so their addresses can't shift.

## 2026-10-10
- Added the four troubleshooting write-ups the README already linked to (`docs/`). They had never been uploaded, so those links were broken.
- Added this changelog and a "last updated" date to the README.
- Split the roadmap into "working on now" and "later". Dropped GNS3, which I no longer use.

## 2026-10-09
- Rack reorganized: patch panel and core switch moved up without unplugging anything, opening a gap for a 1U shelf and a small second server.
- Wrote up Suricata, the local AI server, the rescue-port laptop profile and recent fixes in the README.
- Planning assistant on the local AI server. Found that default document retrieval was dropping parts of the rubric, and fixed it with full-context mode.

## 2026-10-07
- **Suricata IDS** enabled on the firewall: IDS-only mode, three internal interfaces, about 61,000 Emerging Threats Open rules. Snapshot taken first, and the firewall VM raised to 8 GB of memory.
- **Local AI server** built: Ollama (Qwen3 14B) on the desktop GPU, Open WebUI in a container on the server VLAN, and a Windows Firewall rule that only lets that container reach the model.
- Fixed a Nextcloud 503 after an automatic update left the database un-upgraded (snapshot, then `occ upgrade`).
- Break-glass network profile on the laptop for the rescue port, tested.
- Learned not to shut down the firewall VM from a web UI that's reached through that same firewall.

## 2026-10-06
- **Cloudflare Access** in front of the one public service (Uptime Kuma). Fixed a tunnel 502 caused by a route still pointing at the Pi's pre-rebuild address.
- **AI alert helper**: Kuma alerts go to a Cloudflare Worker, Workers AI suggests a likely cause and first checks, and the result is posted to Discord.
- **AI Wazuh digest**: a daily script groups about 10,000 alerts by rule, and only those summaries go to the Worker for a plain-English verdict.
- **Termix** SSH/remote-desktop gateway, HTTPS and TOTP only.
- Fixed the Authentik outpost's own host setting, which was still on plain HTTP.
- SSH is key-only (Ed25519) on the Pi and the DNS/SIEM box.

## 2026-10-05
- Uptime Kuma alerts to Discord.
- **Automated patching**: Ansible through Semaphore, with weekly schedules for the Pi and the secondary resolver.
- Immich photo library moved onto the NAS, with a systemd mount dependency so Docker waits for the share.

## 2026-10-04
- Created this repo: README, topology diagram, Ansible update playbook.
- **Prometheus + Grafana** monitoring replaced Netdata, which had been driving the Pi's Docker daemon to about 118% CPU.
- Second managed switch joined to the core switch by an 802.1Q trunk.
- Wake-on-LAN for the desktop through the firewall.

## 2026-10-02
- Permanent rescue port on the core switch, on the hypervisor's Layer 2 segment.
- Locked myself out of the firewall with its own two-factor login and recovered (hypervisor CLI, rescue port, single-user mode).

---

## Before October 2026 (summary)
- Active Directory domain with AD-integrated DNS, four VLANs behind OPNsense, one-way IoT isolation.
- Second DNS resolver (Pi-hole + Unbound) on separate hardware ([write-up](docs/01-dns-silent-drop.md)).
- Fedora laptop joined to the domain, with full-disk encryption ([Kerberos write-up](docs/02-kerberos-clock-skew.md)).
- WireGuard replaced by Tailscale as subnet router and exit node ([write-up](docs/03-wireguard-to-tailscale.md)).
- Wazuh SIEM with agents on four endpoints.
- Authentik SSO with TOTP. Found and fixed providers sending logins over plain HTTP.
- Returned a NAS that no longer gets security updates. Replaced it with a hardened RAID 1 NAS with snapshots and a nightly off-box copy.
- Passed CompTIA A+.
