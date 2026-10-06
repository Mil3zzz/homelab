export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const key = url.searchParams.get("key");
    if (request.method !== "POST" || key !== env.ALERT_KEY) {
      return new Response("Not found", { status: 404 });
    }

    let data;
    try {
      data = await request.json();
    } catch {
      return new Response("Bad request", { status: 400 });
    }

    const monitor = data.monitor || {};
    const beat = data.heartbeat || {};
    const name = monitor.name || "Test notification";
    const target = monitor.hostname || monitor.url || "n/a";
    const checkType = monitor.type || "n/a";
    const detail = beat.msg || data.msg || "";
    let status = "TEST";
    if (beat.status === 0) status = "DOWN";
    if (beat.status === 1) status = "UP";

    const lab =
      "Home lab: a Proxmox hypervisor (mini PC) runs an OPNsense firewall VM, " +
      "a Windows Server domain controller VM, and Docker containers (Immich photos, " +
      "Authentik SSO, Grafana and Prometheus). A Raspberry Pi runs Uptime Kuma, " +
      "Pi-hole and a Cloudflare Tunnel. A NAS stores photos and backups. " +
      "A second small machine runs a secondary DNS resolver.";

    let text;
    if (status === "UP") {
      text = "✅ **" + name + "** is back up.";
    } else {
      const question =
        status === "DOWN"
          ? lab + "\n\nUptime Kuma says this check is DOWN.\nMonitor: " + name +
            "\nCheck type: " + checkType + "\nTarget: " + target +
            "\nError: " + detail +
            "\n\nWhat is the most likely cause, and what should I check first?"
          : "This is a test of an alert helper. Reply with one short friendly sentence confirming you are working.";

      let advice = "";
      try {
        const ai = await env.AI.run("@cf/meta/llama-3.3-70b-instruct-fp8-fast", {
          messages: [
            {
              role: "system",
              content:
                "You help a student troubleshoot their home lab. Give the most likely " +
                "cause, then 2 or 3 short bullet points of what to check first. " +
                "Stay under 80 words. Do not invent details you were not given.",
            },
            { role: "user", content: question },
          ],
          max_tokens: 200,
        });
        advice = (ai && ai.response) || "";
      } catch (e) {
        console.log("AI error:", e && e.message);
        advice = "(AI note unavailable: " + String((e && e.message) || e).slice(0, 300) + ")";
      }

      const header =
        status === "DOWN"
          ? "🔴 **" + name + "** is DOWN\n" + detail
          : "🧪 **Test alert**";
      text = header + "\n\n🤖 " + advice;
    }

    await fetch(env.DISCORD_WEBHOOK, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content: text.slice(0, 1900) }),
    });

    return new Response("ok");
  },
};
