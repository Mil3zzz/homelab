# Server answers ping but nothing else works

**Symptom:** After a cable cleanup I powered my DNS/SIEM box back on. It replied to ping, but SSH was refused, the Pi-hole web page wouldn't load, and Grafana showed "N/A" for every metric from that host. The machine was clearly up. Its services weren't.

---

## Setup

The box runs Pi-hole, Unbound and Wazuh on Ubuntu Server, and has a 1 TB USB drive that holds the nightly backup. During the cleanup I shut it down properly, rerouted cables, and powered it back on. What I didn't do was plug the USB drive back in first.

## What I ruled out

**Did it get a different IP?** I suspected the address had changed after the power cycle. Ping to the old address got replies, so no.

**Is SSH just on a different port?** The error was `connection refused`, not a timeout. That matters: a timeout means packets are being dropped somewhere, a refusal means the host answered and said nothing is listening. So the network path was fine and the service wasn't running.

**Is the web UI the problem or the whole box?** Pi-hole's page, SSH, and the metrics exporter were all dead at once. Three unrelated services failing together points at something below all of them.

## What I found

I plugged in a monitor and keyboard. The machine had dropped to a root prompt instead of a normal login. Asking systemd how it was doing:

```
systemctl is-system-running
→ maintenance
```

`maintenance` means the system booted into emergency mode. `lsblk` showed the USB drive wasn't present, which lined up with the cleanup.

## Root cause

The drive was listed in `/etc/fstab` with the default options. By default, systemd treats every fstab entry as required for boot. When the drive wasn't there, systemd couldn't mount it, gave up on the rest of startup, and dropped to emergency mode. Networking came up early enough to answer ping, and everything that normally starts after that (SSH, Pi-hole, the exporter) never started.

## Fix

First the immediate fix: plug the drive in and reboot. It came back normally.

Then the permanent one, so a missing drive can't do this again. In `/etc/fstab`, add `nofail` to the drive's options:

```
cp /etc/fstab /etc/fstab.bak
sed -i '/backup-drive/ s/defaults/defaults,nofail/' /etc/fstab
findmnt --verify
systemctl daemon-reload
```

`nofail` tells systemd the mount is optional: if it's missing, skip it and keep booting. My backup script already refuses to run when the drive isn't mounted, so the worst case is now a skipped backup instead of an unreachable server.

## What I took from it

A host that answers ping isn't a healthy host. Ping only proves the network stack is up. The useful move was separating "can I reach it" from "are its services running", and the difference between a refused connection and a timeout told me which one I was dealing with before I touched a keyboard.

Three services failing at the same moment isn't three problems. When unrelated things break together, look for the one thing underneath them, which here was boot itself.

Optional hardware shouldn't be a boot dependency. A backup drive is something the server can live without, so the config should say that. I'd been treating "mounted at boot" as the same as "required at boot", and nothing had ever tested the difference until I made it happen by accident.

It also changed how I do maintenance. I now have a written shutdown runbook that lists what can be unplugged and what needs a clean shutdown, and the drive is only ever moved while the host is off.
