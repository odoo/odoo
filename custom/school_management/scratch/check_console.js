const { spawn } = require('child_process');

async function checkConsole() {
    const chromePath = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
    const chromeProc = spawn(chromePath, [
        "--headless=new",
        "--remote-debugging-port=9231",
        "--disable-extensions",
        "--disable-gpu",
        "--remote-allow-origins=*",
        "about:blank"
    ]);

    let pageTarget = null;
    for (let i = 0; i < 20; i++) {
        await new Promise(r => setTimeout(r, 400));
        try {
            const targetsRes = await fetch("http://localhost:9231/json");
            const targets = await targetsRes.json();
            pageTarget = targets.find(t => t.type === 'page' && !t.url.startsWith('chrome-extension'));
            if (pageTarget) break;
        } catch {}
    }

    try {
        const ws = new WebSocket(pageTarget.webSocketDebuggerUrl);
        await new Promise(r => ws.onopen = r);

        let id = 1;
        const send = (method, params = {}) => new Promise(resolve => {
            const curId = id++;
            const handler = (event) => {
                const data = JSON.parse(event.data);
                if (data.id === curId) {
                    ws.removeEventListener('message', handler);
                    resolve(data.result);
                }
            };
            ws.addEventListener('message', handler);
            ws.send(JSON.stringify({ id: curId, method, params }));
        });

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.method === "Runtime.consoleAPICalled") {
                console.log("[CONSOLE]", data.params.type, data.params.args.map(a => a.value || a.description).join(" "));
            }
            if (data.method === "Runtime.exceptionThrown") {
                console.log("[EXCEPTION]", data.params.exceptionDetails.exception?.description || data.params.exceptionDetails.text);
            }
        };

        await send("Runtime.enable");
        await send("Page.enable");
        await send("Page.navigate", { url: "http://localhost:8070/odoo?debug=assets" });

        await new Promise(r => setTimeout(r, 6000));
        ws.close();
    } finally {
        chromeProc.kill();
    }
}

checkConsole().catch(console.error);
