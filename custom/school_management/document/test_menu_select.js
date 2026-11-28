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
        "--remote-debugging-port=9225",
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
            const targetsRes = await fetch("http://localhost:9225/json");
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

        const menuInfo = await sendCmd("Runtime.evaluate", {
            expression: `(() => {
                const menuService = odoo.__WOWL_DEBUG__.root.env.services.menu;
                const allMenus = menuService.getAll();
                return allMenus.map(m => ({ id: m.id, name: m.name, xmlid: m.xmlid, actionID: m.actionID }));
            })()`,
            returnByValue: true
        });
        console.log("MENUS:", JSON.stringify(menuInfo.result?.value, null, 2));

        // Now test selecting menu
        const regMenu = menuInfo.result?.value?.find(m => m.name.includes("Course Registration"));
        console.log("Selecting menu:", regMenu);
        if (regMenu) {
            await sendCmd("Runtime.evaluate", {
                expression: `(async () => {
                    const menuService = odoo.__WOWL_DEBUG__.root.env.services.menu;
                    await menuService.selectMenu(${regMenu.id});
                })()`,
                awaitPromise: true,
                returnByValue: true
            });
            await new Promise(r => setTimeout(r, 2500));

            const check = await sendCmd("Runtime.evaluate", {
                expression: `(() => {
                    return {
                        title: document.querySelector('.o_breadcrumb')?.innerText || document.title,
                        rows: document.querySelectorAll('.o_data_row, .o_kanban_record').length,
                        bodyText: document.body.innerText.slice(0, 300)
                    };
                })()`,
                returnByValue: true
            });
            console.log("AFTER SELECT MENU:", check.result?.value);
        }

        ws.close();
    } finally {
        chromeProc.kill();
    }
}

test().catch(console.error);
