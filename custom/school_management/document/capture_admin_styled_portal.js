const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const ARTIFACT_DIR = "C:\\Users\\Rith2\\.gemini\\antigravity-acp\\brain\\3bd175fb-29eb-43e3-8471-b3acec6d2bbe";
const DOC_DIR = "c:\\Odoo\\odoo\\custom\\school_management\\document\\student_captures";

function log(msg) {
    process.stdout.write(`[${new Date().toISOString()}] ${msg}\n`);
}

async function run() {
    log("Authenticating student user (student / 1234)...");
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

    // Kill any orphan chrome first
    try {
        const killProc = spawn("taskkill", ["/F", "/IM", "chrome.exe"]);
        await new Promise(r => killProc.on('close', r));
    } catch {}
    await new Promise(r => setTimeout(r, 600));

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
        throw new Error("No Chrome page target found");
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

    log("Opening Student Dashboard action...");
    await sendCmd("Runtime.evaluate", {
        expression: "odoo.__WOWL_DEBUG__.root.env.services.action.doAction('school_management.action_student_dashboard_shell', { clearBreadcrumbs: true })",
        awaitPromise: true
    });
    await new Promise(r => setTimeout(r, 4500));

    // Inspect DOM elements
    const domInspection = await sendCmd("Runtime.evaluate", {
        expression: `(() => {
            const header = document.querySelector('.o_exec_header_card');
            const greeting = header?.querySelector('.o_exec_title')?.innerText || '';
            const subtitle = header?.querySelector('.o_exec_subtitle')?.innerText || '';
            const studentIdBadge = header?.querySelector('.badge.font-monospace')?.innerText || '';
            
            const kpiSection = document.querySelector('.o_kpi_five_section');
            const kpiCards = Array.from(document.querySelectorAll('.o_kpi_metric_card')).map(c => ({
                label: c.querySelector('.o_kpi_metric_label')?.innerText.trim(),
                val: c.querySelector('.o_kpi_metric_value')?.innerText.trim(),
                sub: c.querySelector('.small')?.innerText.trim(),
                hasIconBubble: !!c.querySelector('.o_kpi_icon_bubble')
            }));

            const chartCard = document.querySelector('.o_chart_card');
            const scheduleTitle = chartCard?.querySelector('.o_card_title')?.innerText.trim();
            const dateHeading = chartCard?.querySelector('.fw-semibold.text-dark.small')?.innerText.trim();
            const viewButtons = Array.from(chartCard?.querySelectorAll('.btn-group button') || []).map(b => ({
                text: b.innerText.trim(),
                isDark: b.classList.contains('btn-dark')
            }));

            const weekHeaders = Array.from(document.querySelectorAll('.o_week_day_header')).map(h => ({
                name: h.querySelector('.o_day_name')?.innerText.trim(),
                num: h.querySelector('.o_day_number')?.innerText.trim(),
                isToday: h.classList.contains('is_today')
            }));

            const slotCards = Array.from(document.querySelectorAll('.o_schedule_slot_card')).map(s => ({
                code: s.querySelector('.o_slot_code')?.innerText.trim(),
                title: s.querySelector('.o_slot_title')?.innerText.trim(),
                time: s.querySelector('.o_slot_time')?.innerText.trim(),
                colorClass: Array.from(s.classList).find(c => c.startsWith('o_slot_palette_'))
            }));

            const transcriptTable = document.querySelector('.o_detail_card table');
            const transcriptRows = Array.from(transcriptTable?.querySelectorAll('tbody tr') || []).map(r => ({
                code: r.querySelector('.font-monospace')?.innerText.trim(),
                grade: r.querySelector('td:nth-child(3)')?.innerText.trim(),
                status: r.querySelector('td:nth-child(4) .badge')?.innerText.trim()
            }));

            const quickActionTiles = Array.from(document.querySelectorAll('.o_quick_action_tile')).map(t => ({
                title: t.querySelector('.o_tile_title')?.innerText.trim(),
                hasBubble: !!t.querySelector('.o_op_icon_wrap')
            }));

            return {
                headerExists: !!header,
                greeting,
                subtitle,
                studentIdBadge,
                kpiCount: kpiCards.length,
                kpiCards,
                scheduleTitle,
                dateHeading,
                viewButtons,
                weekHeaderCount: weekHeaders.length,
                todayHeader: weekHeaders.find(h => h.isToday),
                slotCount: slotCards.length,
                slotCards,
                transcriptRowCount: transcriptRows.length,
                transcriptRows,
                quickActionCount: quickActionTiles.length,
                quickActionTiles
            };
        })()`,
        returnByValue: true
    });

    log(`DOM Inspection Results: ${JSON.stringify(domInspection.value, null, 2)}`);

    // Helper to save screenshot
    async function saveScreenshot(filename, fullPage = false) {
        let params = { format: "png" };
        if (fullPage) {
            const layout = await sendCmd("Page.getLayoutMetrics");
            params.clip = {
                x: 0,
                y: 0,
                width: layout.cssContentSize.width || 1920,
                height: layout.cssContentSize.height || 1080,
                scale: 1
            };
            params.captureBeyondViewport = true;
        }
        const shot = await sendCmd("Page.captureScreenshot", params);
        const buf = Buffer.from(shot.data, "base64");
        const docPath = path.join(DOC_DIR, filename);
        const artPath = path.join(ARTIFACT_DIR, filename);
        fs.writeFileSync(docPath, buf);
        fs.writeFileSync(artPath, buf);
        log(`Saved screenshot: ${docPath} & ${artPath}`);
    }

    // 1. Capture Main Dashboard Viewport
    await saveScreenshot("01_admin_styled_student_dashboard.png");

    // 2. Capture Full Page
    await saveScreenshot("02_admin_styled_student_dashboard_fullpage.png", true);

    // 3. Switch to Month view
    log("Switching to Month view...");
    await sendCmd("Runtime.evaluate", {
        expression: `(() => {
            const btns = Array.from(document.querySelectorAll('.btn-group button'));
            const monthBtn = btns.find(b => b.innerText.trim() === 'Month');
            if (monthBtn) monthBtn.click();
        })()`
    });
    await new Promise(r => setTimeout(r, 1200));
    await saveScreenshot("03_admin_styled_month_view.png");

    // 4. Switch to List view
    log("Switching to List view...");
    await sendCmd("Runtime.evaluate", {
        expression: `(() => {
            const btns = Array.from(document.querySelectorAll('.btn-group button'));
            const listBtn = btns.find(b => b.innerText.trim() === 'List');
            if (listBtn) listBtn.click();
        })()`
    });
    await new Promise(r => setTimeout(r, 1200));
    await saveScreenshot("04_admin_styled_list_view.png");

    // Clean up
    ws.close();
    chromeProc.kill();
    log("Verification & capture completed successfully!");
}

run().catch(err => {
    console.error("Test failed:", err);
    process.exit(1);
});
