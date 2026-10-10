# Domain join working, login failing on a correct password

**Symptom:** A Linux workstation joined the domain without any issues and could look up domain users fine — but logging in as one always failed on a password I knew for a fact was right.

---

## Setup

Joining a Fedora machine to Active Directory with `realmd` and SSSD. The join itself was clean:

```
realm list
→ configured: kerberos-member
→ login-formats: %U@domain.local
```

User lookups worked too, which meant SSSD was genuinely talking to the directory, not just pretending:

```
id user@domain.local
→ uid=... gid=... groups=domain users@domain.local
```

Computer object showed up in AD. Everything about the join looked healthy. And every single login attempt at the login screen failed with a password error, using a password I'd literally just set.

## What I checked

Was I even using the right account? Turned out the UPN and the sAMAccountName weren't the same string, and I'd assumed they were. Fixed that — still failed.

Was it genuinely the password? Reset it in AD, made sure it hit complexity requirements. Same failure.

Was this a display manager thing? GDM and SSSD have some known quirks around forced password changes at first login, so I tested Kerberos directly, outside the graphical stack entirely:

```
kinit user@DOMAIN.LOCAL
```

Also failed. That was actually the useful result, because it took the problem completely out of the desktop environment and put it squarely on Kerberos.

## The thing that mattered

Two things were true at once: directory lookups worked fine (`id`, `realm list`, the computer object existing), but authentication failed everywhere, every time.

Those are different mechanisms. Lookups are LDAP. Authentication is Kerberos. So whatever was broken was specific to Kerberos, not to reaching the domain controller generally — because if it were a general reachability or DNS problem, the lookups would've failed too, and they hadn't.

## Root cause

Kerberos tickets carry timestamps and get rejected outright if they fall outside a tight window — usually about five minutes. That's intentional, it's how it defends against replay attacks.

The domain controller's clock was a full day off. Both "set time automatically" and "set time zone automatically" were switched off on the server, so it had never synced to anything and had just drifted on its own.

Every single ticket request was getting bounced for being out of tolerance. The password was never actually the problem.

## Fix

Turned automatic time sync back on and forced it:

```powershell
w32tm /resync /force
```

Login worked on the very next attempt.

A domain controller is supposed to be the time authority for its whole domain, and it needs to sync itself to something reliable to actually be that. Leaving that off doesn't cause a problem right away — it's a slow drift that eventually shows up as something that looks nothing like a clock issue.

## What I took from it

Authentication and directory lookups are genuinely separate systems. I spent longer than I should have assuming that because the machine could see the domain, whatever was failing had to be credentials-related. Splitting "can it read the directory" from "can it get a ticket" is what actually cracked this.

Test underneath the GUI when something graphical fails. `kinit` failing the exact same way GDM did eliminated an entire layer in one command. Any time a login screen rejects something, there's almost always a CLI equivalent worth trying first — it tells you immediately whether you're debugging the desktop or something underneath it.

Clock drift produces errors that point at the wrong thing entirely. Nothing here said "time" anywhere in the error text. It said password rejected. Kerberos, cert validation, TOTP — all of these fail in ways that look like something else entirely when clocks drift, so checking the clock is something I do early now instead of after I've exhausted everything more obvious.
