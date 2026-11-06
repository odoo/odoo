const { spawn } = require('child_process');

async function getFailedModules() {
    const chromePath = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
    const chromeProc = spawn(chromePath, [
        "--headless=new",
        "--remote-debugging-port=9232",
        "--disable-extensions",
        "--disable-gpu",
        "--remote-allow-origins=*",
        "about:blank"
    ]);

    let pageTarget = null;
    for (let i = 0; i < 20; i++) {
        await new Promise(r => setTimeout(r, 400));
        try {
            const targetsRes = await fetch("http://localhost:9232/json");
            const targets = await targetsRes.json();
            pageTarget = targets.find(t => t.type === 'page' && !t.url.startsWith('chrome-extension'));
            if (pageTarget) break;
        } catch {}
    }

    try {
        const ws = new WebSocket(pageTarget.webSocketDebuggerUrl);
        await new Promise(r => ws.onopen = r);

        let id = 1;
        const pending = new Map();
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.id && pending.has(data.id)) {
                const { resolve, reject } = pending.get(data.id);
                pending.delete(data.id);
                if (data.error) reject(data.error);
                else resolve(data.result);
            }
        };

        const send = (method, params = {}) => new Promise((resolve, reject) => {
            pending.set(id, { resolve, reject });
            ws.send(JSON.stringify({ id: id++, method, params }));
        });

        await send("Runtime.enable");
        await send("Page.enable");
        await send("Page.navigate", { url: "http://localhost:8070/odoo" });
        await new Promise(r => setTimeout(r, 6000));

        const res = await send("Runtime.evaluate", {
            expression: `(() => {
                if (!window.odoo || !window.odoo.loader) return "no odoo.loader";
                const failed = window.odoo.loader.failed || [];
                const errors = [];
                for (const [k, v] of (window.odoo.loader.errors || new Map())) {
                    errors.push({ module: k, error: v.message || String(v), stack: v.stack });
                }
                return JSON.stringify({ failed, errors }, null, 2);
            })()`,
            returnByValue: true
        });

        console.log("Loader errors:\n", res.result?.value);
        ws.close();
    } finally {
        chromeProc.kill();
    }
}

getFailedModules().catch(console.error);
