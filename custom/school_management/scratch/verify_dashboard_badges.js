const { spawn } = require('child_process');
const fs = require('fs');

async function testDashboardWithSession() {
    const authResp = await fetch("http://127.0.0.1:8070/web/session/authenticate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            jsonrpc: "2.0",
            params: { db: "odoo", login: "admin", password: "admin" }
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
    console.log("Session ID:", sessionId);

    const chromePath = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
    const port = 9235;
    const chromeProc = spawn(chromePath, [
        "--headless=new",
        `--remote-debugging-port=${port}`,
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
            const targetsRes = await fetch(`http://127.0.0.1:${port}/json`);
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

        await send("Network.enable");
        await send("Page.enable");
        await send("Runtime.enable");

        await send("Network.setCookie", {
            name: "session_id",
            value: sessionId,
            domain: "127.0.0.1",
            path: "/"
        });

        const targetUrl = "http://127.0.0.1:8070/web#action=193";
        console.log("Navigating to", targetUrl);
        await send("Page.navigate", { url: targetUrl });

        let loaded = false;
        for (let i = 0; i < 30; i++) {
            await new Promise(r => setTimeout(r, 1000));
            const check = await send("Runtime.evaluate", {
                expression: `Boolean(document.querySelector('.o_recent_enrollments_card') || document.querySelector('.o_enrollment_table'))`
            });
            if (check.result?.value) {
                console.log(`Found enrollments card after ${i+1}s!`);
                loaded = true;
                break;
            }
        }

        // Evaluate badge HTML inside .o_recent_enrollments_card
        const evalRes = await send("Runtime.evaluate", {
            expression: `(() => {
                const card = document.querySelector('.o_recent_enrollments_card');
                if (!card) return 'Card not found, current views: ' + document.body.innerText.slice(0, 200);
                const rows = Array.from(card.querySelectorAll('tbody tr')).map(tr => {
                    const badge = tr.querySelector('.badge');
                    return {
                        rowText: tr.innerText.trim().replace(/\\s+/g, ' '),
                        badgeText: badge ? badge.innerText : null,
                        badgeClass: badge ? badge.className : null,
                        badgeColor: badge ? window.getComputedStyle(badge).color : null,
                        badgeBg: badge ? window.getComputedStyle(badge).backgroundColor : null,
                        badgeBorder: badge ? window.getComputedStyle(badge).borderColor : null,
                    };
                });
                return JSON.stringify(rows, null, 2);
            })()`,
            returnByValue: true
        });

        console.log("Evaluation Result:\n", evalRes.result?.value);

        // Capture screenshot of the table or viewport
        const ss = await send("Page.captureScreenshot", { format: "png" });
        fs.writeFileSync("scratch/dashboard_verified.png", Buffer.from(ss.data, "base64"));
        console.log("Saved screenshot to scratch/dashboard_verified.png");

        ws.close();
    } finally {
        chromeProc.kill();
    }
}

testDashboardWithSession().catch(console.error);
