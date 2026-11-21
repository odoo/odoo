const { spawn } = require('child_process');

async function test() {
    const authResp = await fetch("http://localhost:8070/web/session/authenticate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            jsonrpc: "2.0",
            params: { db: "odoo", login: "student", password: "1234" }
        })
    });

    const setCookies = authResp.headers.getSetCookie ? authResp.headers.getSetCookie() : [authResp.headers.get('set-cookie')];
    let sessionId = null;
    for (const c of setCookies) {
        if (!c) continue;
        for (const part of c.split(';')) {
            if (part.trim().startsWith('session_id=')) {
                sessionId = part.trim().split('=')[1];
                break;
            }
        }
    }

    const chromePath = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
    const chromeProc = spawn(chromePath, [
        "--headless=new",
        "--remote-debugging-port=9224",
        "--disable-extensions",
        "--disable-gpu",
        "--remote-allow-origins=*",
        "--window-size=1920,1080",
        "about:blank"
    ]);

    let pageTarget = null;
    for (let i = 0; i < 20; i++) {
        await new Promise(r => setTimeout(r, 400));
        try {
            const targetsRes = await fetch("http://localhost:9224/json");
            const targets = await targetsRes.json();
            pageTarget = targets.find(t => t.type === 'page' && !t.url.startsWith('chrome-extension'));
            if (pageTarget) break;
        } catch {}
    }

    try {
        const ws = new WebSocket(pageTarget.webSocketDebuggerUrl);
        await new Promise((resolve, reject) => {
            ws.onopen = resolve;
            ws.onerror = reject;
        });

        let idCounter = 1;
        const pending = new Map();
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.method === "Runtime.consoleAPICalled") {
                console.log("[CONSOLE]", data.params.type, data.params.args.map(a => a.value || a.description).join(" "));
            }
            if (data.method === "Runtime.exceptionThrown") {
                console.log("[EXCEPTION]", JSON.stringify(data.params.exceptionDetails));
            }
            if (data.id && pending.has(data.id)) {
                const { resolve, reject } = pending.get(data.id);
                pending.delete(data.id);
                if (data.error) reject(data.error);
                else resolve(data.result);
            }
        };

        function sendCmd(method, params = {}) {
            const id = idCounter++;
            return new Promise((resolve, reject) => {
                pending.set(id, { resolve, reject });
                ws.send(JSON.stringify({ id, method, params }));
            });
        }

        await sendCmd("Page.enable");
        await sendCmd("Network.enable");
        await sendCmd("Runtime.enable");

        await sendCmd("Network.setCookie", {
            name: "session_id",
            value: sessionId,
            domain: "localhost",
            path: "/"
        });

        await sendCmd("Page.navigate", { url: "http://localhost:8070/odoo" });
        await new Promise(r => setTimeout(r, 4000));

        console.log("Navigating to action 919...");
        const evalRes = await sendCmd("Runtime.evaluate", {
            expression: `(async () => {
                const actionService = odoo.__WOWL_DEBUG__.root.env.services.action;
                await actionService.doAction(919, { clearBreadcrumbs: true });
                await new Promise(r => setTimeout(r, 2000));
                return {
                    breadcrumb: document.querySelector('.o_breadcrumb, .breadcrumb')?.innerText,
                    controlPanel: document.querySelector('.o_control_panel')?.innerText,
                    contentHTML: document.querySelector('.o_content')?.innerHTML.slice(0, 500),
                    actionManagerHTML: document.querySelector('.o_action_manager')?.innerHTML.slice(0, 500)
                };
            })()`,
            awaitPromise: true,
            returnByValue: true
        });

        console.log("DOM RESULT:", JSON.stringify(evalRes.result?.value, null, 2));
        ws.close();
    } finally {
        chromeProc.kill();
    }
}

test().catch(console.error);
