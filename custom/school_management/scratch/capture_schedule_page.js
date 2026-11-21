const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const ARTIFACT_DIR = "C:\\Users\\Rith2\\.gemini\\antigravity\\brain\\04dd9293-b979-4b90-a61b-cd709d86fc01";

function log(msg) {
    process.stdout.write(`[${new Date().toISOString()}] ${msg}\n`);
}

async function main() {
    log("Authenticating student user...");
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
    log(`Session ID acquired: ${sessionId ? 'OK' : 'FAILED'}`);

    const chromePath = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
    const port = 9247;
    const chromeProc = spawn(chromePath, [
        "--headless=new",
        `--remote-debugging-port=${port}`,
        "--disable-extensions",
        "--disable-gpu",
        "--remote-allow-origins=*",
        "--window-size=1680,1050",
        "about:blank"
    ]);

    let pageTarget = null;
    for (let i = 0; i < 25; i++) {
        await new Promise(r => setTimeout(r, 400));
        try {
            const targetsRes = await fetch(`http://localhost:${port}/json`);
            const targets = await targetsRes.json();
            pageTarget = targets.find(t => t.type === 'page' && !t.url.startsWith('chrome-extension'));
            if (pageTarget) break;
        } catch {}
    }

    if (!pageTarget) {
        log("Could not find chrome page target");
        chromeProc.kill();
        process.exit(1);
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
                const text = data.params.args.map(a => a.value || a.description || JSON.stringify(a)).join(' ');
                log(`[BROWSER CONSOLE] ${data.params.type}: ${text.substring(0, 300)}`);
            } else if (data.method === "Runtime.exceptionThrown") {
                log(`[BROWSER EXCEPTION] ${JSON.stringify(data.params.exceptionDetails)}`);
            }

            if (data.id && pending.has(data.id)) {
                const { resolve, reject } = pending.get(data.id);
                pending.delete(data.id);
                if (data.error) reject(data.error);
                else resolve(data.result);
            }
        };

        function send(method, params = {}) {
            return new Promise((resolve, reject) => {
                const id = idCounter++;
                pending.set(id, { resolve, reject });
                ws.send(JSON.stringify({ id, method, params }));
            });
        }

        await send("Page.enable");
        await send("Network.enable");
        await send("Runtime.enable");

        await send("Network.setCookie", {
            name: "session_id",
            value: sessionId,
            domain: "localhost",
            path: "/"
        });
        await send("Network.setCookie", {
            name: "session_id",
            value: sessionId,
            domain: "127.0.0.1",
            path: "/"
        });

        const targetUrl = "http://localhost:8070/odoo/action-school_management.action_university_schedule_view";
        log(`Navigating to ${targetUrl}...`);
        await send("Page.navigate", { url: targetUrl });

        let loaded = false;
        for (let i = 0; i < 60; i++) {
            await new Promise(r => setTimeout(r, 500));
            const checkRes = await send("Runtime.evaluate", {
                expression: `Boolean(document.querySelector('.o_university_schedule_wrapper') || document.querySelector('.o_schedule_columns_container'))`
            });
            if (checkRes.result?.value) {
                log(`Found schedule element after ${i * 0.5}s!`);
                loaded = true;
                break;
            }
        }

        if (!loaded) {
            const bodyRes = await send("Runtime.evaluate", {
                expression: `({ title: document.title, bodyLength: document.body.innerHTML.length, textSnippet: document.body.innerText.substring(0, 200) })`
            });
            log(`Page state after timeout: ${JSON.stringify(bodyRes.result?.value)}`);
        }

        await new Promise(r => setTimeout(r, 2000));

        const screenshot = await send("Page.captureScreenshot", {
            format: "png",
            quality: 95
        });

        const buf = Buffer.from(screenshot.data, "base64");
        const outPath = path.join(ARTIFACT_DIR, "schedule_current_state.png");
        fs.writeFileSync(outPath, buf);
        log(`Saved screenshot to ${outPath}`);

        ws.close();
    } catch (e) {
        log(`Error: ${e.message}`);
    } finally {
        chromeProc.kill();
    }
}

main().catch(err => console.error(err));
