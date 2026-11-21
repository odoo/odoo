const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const ARTIFACT_DIR = "C:\\Users\\Rith2\\.gemini\\antigravity\\brain\\d2f63eba-92d4-4a4f-82f0-30d07a28d49f";
const DOC_DIR = "c:\\Odoo\\odoo\\custom\\school_management\\document\\student_captures";

function log(msg) {
    process.stdout.write(`[${new Date().toISOString()}] ${msg}\n`);
}

async function run() {
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
        for (const p of c.split(';')) {
            if (p.trim().startsWith('session_id=')) sessionId = p.trim().split('=')[1];
        }
    }
    log(`Student Session ID: ${sessionId}`);

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
    if (!pageTarget) {
        chromeProc.kill();
        throw new Error("No page target found");
    }

    const ws = new WebSocket(pageTarget.webSocketDebuggerUrl);
    await new Promise(r => ws.onopen = r);

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
    await sendCmd("Runtime.enable");
    await sendCmd("Network.enable");
    await sendCmd("Network.setCookie", { name: "session_id", value: sessionId, domain: "localhost", path: "/" });
    await sendCmd("Page.navigate", { url: "http://localhost:8070/odoo" });
    await new Promise(r => setTimeout(r, 4500));

    log("Opening Student Dashboard (Action 198)...");
    await sendCmd("Runtime.evaluate", {
        expression: "odoo.__WOWL_DEBUG__.root.env.services.action.doAction(198, { clearBreadcrumbs: true })",
        awaitPromise: true
    });
    await new Promise(r => setTimeout(r, 4000));

    // 1. Calendar View (Default)
    const calData = await sendCmd("Runtime.evaluate", {
        expression: `(() => {
            const switcher = document.querySelector('.o_schedule_view_switcher');
            const activeBtn = switcher?.querySelector('button.active')?.innerText.trim();
            const cards = Array.from(document.querySelectorAll('.o_cal_slot_card')).map(c => c.innerText.replace(/\\n+/g, ' | '));
            return { activeBtn, count: cards.length, cards };
        })()`,
        returnByValue: true
    });
    log(`CALENDAR (DEFAULT) VIEW:\n${JSON.stringify(calData.result?.value, null, 2)}`);

    const snapCal = await sendCmd("Page.captureScreenshot", { format: "png" });
    fs.writeFileSync(path.join(DOC_DIR, "01_dashboard_schedule_calendar.png"), Buffer.from(snapCal.data, 'base64'));
    fs.writeFileSync(path.join(ARTIFACT_DIR, "01_dashboard_schedule_calendar.png"), Buffer.from(snapCal.data, 'base64'));
    log("Saved 01_dashboard_schedule_calendar.png");

    // 2. Switch to Kanban View
    log("Switching to Kanban view...");
    await sendCmd("Runtime.evaluate", {
        expression: `(() => {
            const btn = Array.from(document.querySelectorAll('.o_schedule_view_switcher button')).find(b => b.innerText.includes('Kanban'));
            if (btn) btn.click();
        })()`
    });
    await new Promise(r => setTimeout(r, 1500));

    const kanbanData = await sendCmd("Runtime.evaluate", {
        expression: `(() => {
            const switcher = document.querySelector('.o_schedule_view_switcher');
            const activeBtn = switcher?.querySelector('button.active')?.innerText.trim();
            const cards = Array.from(document.querySelectorAll('.o_kanban_session_card')).map(c => c.innerText.replace(/\\n+/g, ' | '));
            return { activeBtn, count: cards.length, cards };
        })()`,
        returnByValue: true
    });
    log(`KANBAN VIEW:\n${JSON.stringify(kanbanData.result?.value, null, 2)}`);

    const snapKanban = await sendCmd("Page.captureScreenshot", { format: "png" });
    fs.writeFileSync(path.join(DOC_DIR, "02_dashboard_schedule_kanban.png"), Buffer.from(snapKanban.data, 'base64'));
    fs.writeFileSync(path.join(ARTIFACT_DIR, "02_dashboard_schedule_kanban.png"), Buffer.from(snapKanban.data, 'base64'));
    log("Saved 02_dashboard_schedule_kanban.png");

    // 3. Switch to Gantt View
    log("Switching to Gantt view...");
    await sendCmd("Runtime.evaluate", {
        expression: `(() => {
            const btn = Array.from(document.querySelectorAll('.o_schedule_view_switcher button')).find(b => b.innerText.includes('Gantt'));
            if (btn) btn.click();
        })()`
    });
    await new Promise(r => setTimeout(r, 1500));

    const ganttData = await sendCmd("Runtime.evaluate", {
        expression: `(() => {
            const switcher = document.querySelector('.o_schedule_view_switcher');
            const activeBtn = switcher?.querySelector('button.active')?.innerText.trim();
            const bars = Array.from(document.querySelectorAll('.o_gantt_bar')).map(b => b.innerText.replace(/\\n+/g, ' | ') + ' [Title: ' + b.getAttribute('title') + ']');
            return { activeBtn, count: bars.length, bars };
        })()`,
        returnByValue: true
    });
    log(`GANTT VIEW:\n${JSON.stringify(ganttData.result?.value, null, 2)}`);

    const snapGantt = await sendCmd("Page.captureScreenshot", { format: "png" });
    fs.writeFileSync(path.join(DOC_DIR, "03_dashboard_schedule_gantt.png"), Buffer.from(snapGantt.data, 'base64'));
    fs.writeFileSync(path.join(ARTIFACT_DIR, "03_dashboard_schedule_gantt.png"), Buffer.from(snapGantt.data, 'base64'));
    log("Saved 03_dashboard_schedule_gantt.png");

    // 4. Switch to Schedule Tab
    log("Switching to Schedule Tab...");
    await sendCmd("Runtime.evaluate", {
        expression: `(() => {
            const schedTab = Array.from(document.querySelectorAll('.o_student_dashboard_nav button, .nav-link')).find(b => b.innerText.includes('Schedule'));
            if (schedTab) schedTab.click();
        })()`
    });
    await new Promise(r => setTimeout(r, 1500));

    const snapTab = await sendCmd("Page.captureScreenshot", { format: "png" });
    fs.writeFileSync(path.join(DOC_DIR, "04_dashboard_tab_schedule.png"), Buffer.from(snapTab.data, 'base64'));
    fs.writeFileSync(path.join(ARTIFACT_DIR, "04_dashboard_tab_schedule.png"), Buffer.from(snapTab.data, 'base64'));
    log("Saved 04_dashboard_tab_schedule.png");

    chromeProc.kill();
    log("All captures completed successfully!");
}

run().catch(e => {
    log("ERR: " + e.message);
    process.exit(1);
});
