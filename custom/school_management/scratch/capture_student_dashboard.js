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
    const port = 9245;
    const chromeProc = spawn(chromePath, [
        "--headless=new",
        `--remote-debugging-port=${port}`,
        "--disable-extensions",
        "--disable-gpu",
        "--remote-allow-origins=*",
        "--window-size=1680,1380",
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
        await send("Network.setCookie", {
            name: "session_id",
            value: sessionId,
            domain: "127.0.0.1",
            path: "/"
        });

        // In Odoo, navigating to /odoo?cids=1 or /web#action=school_management.action_student_dashboard_shell
        const targetUrl = "http://localhost:8070/odoo/action-school_management.action_student_dashboard_shell";
        log(`Navigating to ${targetUrl}...`);
        await send("Page.navigate", { url: targetUrl });

        for (let i = 0; i < 40; i++) {
            await new Promise(r => setTimeout(r, 500));
            const checkRes = await send("Runtime.evaluate", {
                expression: `Boolean(document.querySelector('.o_student_portal_dashboard') || document.querySelector('.o_student_portal_root'))`
            });
            if (checkRes.result?.value) {
                log(`Found student portal dashboard element after ${i * 0.5}s!`);
                break;
            }
        }

        await new Promise(r => setTimeout(r, 3000));

        // Evaluate dashboard presence and content
        const evalRes = await send("Runtime.evaluate", {
            expression: `({
                title: document.title,
                url: window.location.href,
                hasDashboard: Boolean(document.querySelector('.o_student_portal_dashboard')),
                greetingText: document.querySelector('.o_student_greeting_card h1')?.textContent?.trim(),
                greetingIdText: document.querySelector('.o_student_greeting_card')?.textContent?.includes('ID:'),
                advisorText: document.querySelector('.o_advisor_pill')?.textContent?.trim(),
                kpiCards: Array.from(document.querySelectorAll('.o_kpi_card')).map(c => ({
                    title: c.querySelector('.fw-semibold')?.textContent?.trim(),
                    value: c.querySelector('.h2')?.textContent?.trim()
                })),
                scheduleHeader: document.querySelector('.o_dashboard_middle_card h2')?.textContent?.trim(),
                scheduleSubtitle: document.querySelector('.o_dashboard_middle_card .text-muted.small')?.textContent?.trim(),
                scheduleLiveBadge: document.querySelector('.o_badge_live')?.textContent?.trim(),
                urgentCardCount: document.querySelectorAll('.o_asg_urgent_card').length,
                bottomCards: Array.from(document.querySelectorAll('.o_dashboard_bottom_card')).map(c => c.querySelector('h2')?.textContent?.trim()),
                evalBannerText: document.querySelector('.o_eval_callout_banner')?.textContent?.trim()?.replace(/\\s+/g, ' ')
            })`,
            returnByValue: true
        });
        log(`Dashboard diagnostics: ${JSON.stringify(evalRes.result?.value, null, 2)}`);

        // Capture screenshot of the full dashboard
        const screenshot = await send("Page.captureScreenshot", {
            format: "png",
            captureBeyondViewport: false
        });
        const outPath = path.join(ARTIFACT_DIR, "student_dashboard_redesigned.png");
        fs.writeFileSync(outPath, Buffer.from(screenshot.data, "base64"));
        log(`Saved screenshot to ${outPath}`);

        // Click Tomorrow tab
        log("Testing tab click 'Tomorrow (Thu)'...");
        await send("Runtime.evaluate", {
            expression: `(() => {
                const btns = Array.from(document.querySelectorAll('.o_schedule_tab_btn'));
                const tmBtn = btns.find(b => b.textContent.includes('Tomorrow'));
                if (tmBtn) {
                    tmBtn.click();
                    return "Clicked Tomorrow";
                }
                return "Tomorrow button not found";
            })()`
        });
        await new Promise(r => setTimeout(r, 1000));

        const tabSwitchRes = await send("Runtime.evaluate", {
            expression: `({
                scheduleHeader: document.querySelector('.o_dashboard_middle_card h2')?.textContent?.trim(),
                scheduleSubtitle: document.querySelector('.o_dashboard_middle_card .text-muted.small')?.textContent?.trim()
            })`,
            returnByValue: true
        });
        log(`After Tomorrow click: ${JSON.stringify(tabSwitchRes.result?.value)}`);

        // Capture Tomorrow tab screenshot
        const screenshotTm = await send("Page.captureScreenshot", {
            format: "png",
            captureBeyondViewport: false
        });
        const outPathTm = path.join(ARTIFACT_DIR, "student_dashboard_tomorrow_tab.png");
        fs.writeFileSync(outPathTm, Buffer.from(screenshotTm.data, "base64"));
        log(`Saved Tomorrow tab screenshot to ${outPathTm}`);

        ws.close();
    } finally {
        chromeProc.kill();
    }
}

main().catch(err => {
    console.error("Fatal error:", err);
    process.exit(1);
});
