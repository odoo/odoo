const { spawn } = require('child_process');

async function main() {
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
        "--remote-debugging-port=9222",
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
            const targetsRes = await fetch("http://localhost:9222/json");
            const targets = await targetsRes.json();
            pageTarget = targets.find(t => t.type === 'page' && !t.url.startsWith('chrome-extension'));
            if (pageTarget) break;
        } catch {}
    }

    const ws = new WebSocket(pageTarget.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => { ws.onopen = resolve; ws.onerror = reject; });

    let idCounter = 1;
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
    if (sessionId) {
        await sendCmd("Network.setCookie", {
            name: "session_id", value: sessionId, domain: "localhost", path: "/"
        });
    }

    await sendCmd("Page.navigate", { url: "http://localhost:8070/odoo" });
    await new Promise(r => setTimeout(r, 4000));

    // Try doAction for 836 (My Classes)
    console.log("Calling doAction(836)...");
    const doActionRes = await sendCmd("Runtime.evaluate", {
        expression: `(() => {
            if (window.odoo && odoo.__WOWL_DEBUG__ && odoo.__WOWL_DEBUG__.root) {
                odoo.__WOWL_DEBUG__.root.env.services.action.doAction(836);
                return "doAction called via WOWL_DEBUG";
            }
            return "WOWL_DEBUG not found";
        })()`,
        returnByValue: true
    });
    console.log("Result:", doActionRes.result?.value);
    await new Promise(r => setTimeout(r, 3000));

    const checkView = await sendCmd("Runtime.evaluate", {
        expression: `(() => {
            return {
                title: document.title,
                kanbanCards: document.querySelectorAll('.o_kanban_record').length,
                breadcrumb: document.querySelector('.breadcrumb')?.innerText,
                classes: document.body.innerText.slice(0, 300)
            };
        })()`,
        returnByValue: true
    });
    console.log("Check view:", checkView.result?.value);

    ws.close();
    chromeProc.kill();
}

main().catch(console.error);
