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
        for (part of c.split(';')) {
            if (part.trim().startsWith('session_id=')) {
                sessionId = part.trim().split('=')[1];
                break;
            }
        }
    }

    const chromePath = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
    const chromeProc = spawn(chromePath, [
        "--headless=new",
        "--remote-debugging-port=9226",
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
            const targetsRes = await fetch("http://localhost:9226/json");
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

        console.log("Testing open student form...");
        const evalRes = await sendCmd("Runtime.evaluate", {
            expression: `(async () => {
                try {
                    const actionService = odoo.__WOWL_DEBUG__.root.env.services.action;
                    const res = await actionService.doAction({
                        type: 'ir.actions.act_window',
                        res_model: 'university.student',
                        res_id: 6,
                        views: [[false, 'form']],
                        view_mode: 'form',
                        target: 'current'
                    });
                    console.log("res:", res);
                    await new Promise(r => setTimeout(r, 2000));
                    return {
                        title: document.querySelector('.o_breadcrumb')?.innerText,
                        form: !!document.querySelector('.o_form_view')
                    };
                } catch (e) {
                    console.error("CAUGHT EXCEPTION:", e);
                    const cause = e.cause || {};
                    return {
                        error: e.message,
                        causeMsg: cause.message || String(cause),
                        causeData: cause.data || null,
                        causeStack: cause.stack || null
                    };
                }
            })()`,
            awaitPromise: true,
            returnByValue: true
        });
        console.log("STUDENT FORM RESULT:", evalRes.result?.value);

        console.log("Testing open payment wizard...");
        const wizRes = await sendCmd("Runtime.evaluate", {
            expression: `(async () => {
                try {
                    const actionService = odoo.__WOWL_DEBUG__.root.env.services.action;
                    const res = await actionService.doAction({
                        type: 'ir.actions.act_window',
                        res_model: 'university.fee.payment.wizard',
                        views: [[false, 'form']],
                        view_mode: 'form',
                        target: 'new',
                        context: { default_student_id: 6 }
                    });
                    await new Promise(r => setTimeout(r, 2000));
                    return {
                        modalTitle: document.querySelector('.modal-title')?.innerText,
                        modalBody: document.querySelector('.modal-body')?.innerText?.slice(0, 200)
                    };
                } catch (e) {
                    console.error("WIZARD EXCEPTION:", e);
                    const cause = e.cause || {};
                    return {
                        error: e.message,
                        causeMsg: cause.message || String(cause),
                        causeData: cause.data || null,
                        causeStack: cause.stack || null
                    };
                }
            })()`,
            awaitPromise: true,
            returnByValue: true
        });
        console.log("PAYMENT WIZARD RESULT:", wizRes.result?.value);

        ws.close();
    } finally {
        chromeProc.kill();
    }
}

test().catch(console.error);
