const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const ARTIFACT_DIR = "C:\\Users\\Rith2\\.gemini\\antigravity\\brain\\3584ec4b-f1ee-4bd5-8261-cdf1d00e8e60";

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
    const port = 9260;
    const chromeProc = spawn(chromePath, [
        "--headless=new",
        `--remote-debugging-port=${port}`,
        "--disable-extensions",
        "--disable-gpu",
        "--remote-allow-origins=*",
        "--window-size=1600,1100",
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

        const targetUrl = "http://localhost:8070/odoo?action=198";
        log(`Navigating to ${targetUrl}...`);
        await send("Page.navigate", { url: targetUrl });

        for (let i = 0; i < 35; i++) {
            await new Promise(r => setTimeout(r, 500));
            const checkRes = await send("Runtime.evaluate", {
                expression: `Boolean(document.querySelector('.o_student_portal_root') || document.querySelector('.o_student_navbar'))`
            });
            if (checkRes.result?.value) {
                log(`Found student portal root element after ${i * 0.5}s!`);
                break;
            }
        }

        await new Promise(r => setTimeout(r, 3000));

        // Evaluate dashboard presence and content
        const evalRes = await send("Runtime.evaluate", {
            expression: `({
                title: document.title,
                url: window.location.href,
                hasNavbar: Boolean(document.querySelector('.o_student_navbar')),
                studentName: document.querySelector('.o_student_navbar h1')?.textContent?.trim(),
                hasSidebar: Boolean(document.querySelector('.o_student_sidebar') || document.querySelector('.o_exec_sidebar')),
                navPills: Array.from(document.querySelectorAll('.o_student_nav_pills .nav-link')).map(b => b.textContent.trim().replace(/\\s+/g, ' ')),
                welcomeHeading: document.querySelector('.o_student_welcome_hero h2')?.textContent?.trim(),
                kpiCards: Array.from(document.querySelectorAll('.o_kpi_card_white')).map(c => ({
                    title: c.querySelector('.fw-semibold')?.textContent?.trim(),
                    value: c.querySelector('.h3')?.textContent?.trim()
                })),
                errorAlert: document.querySelector('.o_error_dialog, .o_notification_manager')?.textContent?.trim() || null
            })`,
            returnByValue: true
        });

        log("Evaluated State: " + JSON.stringify(evalRes.result?.value, null, 2));

        // Capture screenshot
        const screenshotRes = await send("Page.captureScreenshot", { format: "png" });
        const screenshotPath = path.join(ARTIFACT_DIR, "student_dashboard_improved.png");
        fs.writeFileSync(screenshotPath, Buffer.from(screenshotRes.data, "base64"));
        log(`Saved screenshot to ${screenshotPath}`);

        ws.close();
    } catch (err) {
        log(`Error: ${err.message}`);
    } finally {
        chromeProc.kill();
    }
}

main().catch(err => {
    log(`Fatal: ${err.message}`);
    process.exit(1);
});
