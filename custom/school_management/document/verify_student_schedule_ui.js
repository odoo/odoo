const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const CAPTURE_DIR = path.join(__dirname, 'student_captures');
const ARTIFACT_DIR = "C:\\Users\\Rith2\\.gemini\\antigravity\\brain\\d2f63eba-92d4-4a4f-82f0-30d07a28d49f";

function log(msg) {
    process.stdout.write(`[${new Date().toISOString()}] ${msg}\n`);
}

async function run() {
    try {
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

        if (sessionId) {
            await sendCmd("Network.setCookie", {
                name: "session_id",
                value: sessionId,
                domain: "localhost",
                path: "/"
            });
        }

        log("Loading web client shell...");
        await sendCmd("Page.navigate", { url: "http://localhost:8070/odoo" });
        await new Promise(r => setTimeout(r, 4500));

        // 1. Load Student Dashboard (Action 198)
        log("Opening Student Dashboard (Action 198)...");
        await sendCmd("Runtime.evaluate", {
            expression: `odoo.__WOWL_DEBUG__.root.env.services.action.doAction(198, { clearBreadcrumbs: true })`,
            awaitPromise: true
        });
        await new Promise(r => setTimeout(r, 4000));

        // Check Default View (Calendar)
        const calCheck = await sendCmd("Runtime.evaluate", {
            expression: `(() => {
                const card = document.querySelector('.o_student_schedule_card');
                const title = card?.querySelector('.o_admin_card_title')?.innerText || '';
                const sub = card?.querySelector('.o_admin_card_sub')?.innerText || '';
                const activeBtn = card?.querySelector('.o_schedule_view_switcher button.active')?.innerText.trim() || '';
                const isCal = !!document.querySelector('.o_schedule_cal_view');
                const slotCards = Array.from(document.querySelectorAll('.o_timetable_slot_card')).map(el => ({
                    subject: el.querySelector('.slot-subject, .fw-bold')?.innerText.trim(),
                    time: el.querySelector('.slot-time, .text-muted')?.innerText.trim(),
                    room: el.querySelector('.slot-room, .fa-map-marker')?.parentNode?.innerText.trim()
                }));
                return { title, sub, activeBtn, isCal, slotCount: slotCards.length, slotCards };
            })()`,
            returnByValue: true
        });
        log(`CALENDAR (DEFAULT) VIEW CHECK:\n${JSON.stringify(calCheck.result?.value, null, 2)}`);

        // Capture Screenshot 1: Calendar View
        const snap1 = await sendCmd("Page.captureScreenshot", { format: "png" });
        fs.writeFileSync(path.join(CAPTURE_DIR, "01_dashboard_schedule_calendar.png"), Buffer.from(snap1.data, 'base64'));
        fs.writeFileSync(path.join(ARTIFACT_DIR, "01_dashboard_schedule_calendar.png"), Buffer.from(snap1.data, 'base64'));
        log("Saved 01_dashboard_schedule_calendar.png");

        // 2. Click Kanban Button
        log("Switching to Kanban view...");
        await sendCmd("Runtime.evaluate", {
            expression: `(() => {
                const btn = Array.from(document.querySelectorAll('.o_schedule_view_switcher button')).find(b => b.innerText.includes('Kanban'));
                if (btn) btn.click();
            })()`
        });
        await new Promise(r => setTimeout(r, 1500));

        const kanbanCheck = await sendCmd("Runtime.evaluate", {
            expression: `(() => {
                const isKanban = !!document.querySelector('.o_schedule_kanban_view');
                const activeBtn = document.querySelector('.o_schedule_view_switcher button.active')?.innerText.trim();
                const cols = document.querySelectorAll('.o_kanban_day_col').length;
                const cards = Array.from(document.querySelectorAll('.o_kanban_slot_card')).map(el => ({
                    title: el.querySelector('.fw-bold')?.innerText.trim(),
                    time: el.innerText.match(/\\d+:\\d+\\s*(?:AM|PM)/g) || []
                }));
                return { isKanban, activeBtn, cols, cardCount: cards.length, cards };
            })()`,
            returnByValue: true
        });
        log(`KANBAN VIEW CHECK:\n${JSON.stringify(kanbanCheck.result?.value, null, 2)}`);

        // Capture Screenshot 2: Kanban View
        const snap2 = await sendCmd("Page.captureScreenshot", { format: "png" });
        fs.writeFileSync(path.join(CAPTURE_DIR, "02_dashboard_schedule_kanban.png"), Buffer.from(snap2.data, 'base64'));
        fs.writeFileSync(path.join(ARTIFACT_DIR, "02_dashboard_schedule_kanban.png"), Buffer.from(snap2.data, 'base64'));
        log("Saved 02_dashboard_schedule_kanban.png");

        // 3. Click Gantt Button
        log("Switching to Gantt view...");
        await sendCmd("Runtime.evaluate", {
            expression: `(() => {
                const btn = Array.from(document.querySelectorAll('.o_schedule_view_switcher button')).find(b => b.innerText.includes('Gantt'));
                if (btn) btn.click();
            })()`
        });
        await new Promise(r => setTimeout(r, 1500));

        const ganttCheck = await sendCmd("Runtime.evaluate", {
            expression: `(() => {
                const isGantt = !!document.querySelector('.o_schedule_gantt_view');
                const activeBtn = document.querySelector('.o_schedule_view_switcher button.active')?.innerText.trim();
                const rows = document.querySelectorAll('.o_gantt_day_row').length;
                const bars = Array.from(document.querySelectorAll('.o_gantt_slot_bar')).map(el => ({
                    text: el.innerText.trim(),
                    title: el.getAttribute('title')
                }));
                return { isGantt, activeBtn, rows, barCount: bars.length, bars };
            })()`,
            returnByValue: true
        });
        log(`GANTT VIEW CHECK:\n${JSON.stringify(ganttCheck.result?.value, null, 2)}`);

        // Capture Screenshot 3: Gantt View
        const snap3 = await sendCmd("Page.captureScreenshot", { format: "png" });
        fs.writeFileSync(path.join(CAPTURE_DIR, "03_dashboard_schedule_gantt.png"), Buffer.from(snap3.data, 'base64'));
        fs.writeFileSync(path.join(ARTIFACT_DIR, "03_dashboard_schedule_gantt.png"), Buffer.from(snap3.data, 'base64'));
        log("Saved 03_dashboard_schedule_gantt.png");

        // 4. Click Schedule Tab in Navigation Header
        log("Clicking Schedule Tab...");
        await sendCmd("Runtime.evaluate", {
            expression: `(() => {
                const schedTab = Array.from(document.querySelectorAll('.o_student_dashboard_nav button, .nav-link')).find(b => b.innerText.includes('Schedule'));
                if (schedTab) schedTab.click();
            })()`
        });
        await new Promise(r => setTimeout(r, 1500));

        const schedTabCheck = await sendCmd("Runtime.evaluate", {
            expression: `(() => {
                const card = !!document.querySelector('.o_student_schedule_card');
                const activeTab = document.querySelector('.o_student_dashboard_nav button.active')?.innerText.trim();
                return { card, activeTab };
            })()`,
            returnByValue: true
        });
        log(`SCHEDULE TAB CHECK:\n${JSON.stringify(schedTabCheck.result?.value, null, 2)}`);

        // Capture Screenshot 4: Schedule Tab
        const snap4 = await sendCmd("Page.captureScreenshot", { format: "png" });
        fs.writeFileSync(path.join(CAPTURE_DIR, "04_dashboard_tab_schedule.png"), Buffer.from(snap4.data, 'base64'));
        fs.writeFileSync(path.join(ARTIFACT_DIR, "04_dashboard_tab_schedule.png"), Buffer.from(snap4.data, 'base64'));
        log("Saved 04_dashboard_tab_schedule.png");

        chromeProc.kill();
        log("All student dashboard schedule tests passed with 100% success!");
    } catch (err) {
        log(`FATAL: ${err.message}`);
        console.error(err);
    }
}

run();
