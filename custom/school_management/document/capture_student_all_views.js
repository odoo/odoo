const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const ARTIFACT_DIR = "C:\\Users\\Rith2\\.gemini\\antigravity\\brain\\04dd9293-b979-4b90-a61b-cd709d86fc01";
const DOC_DIR = "c:\\Odoo\\odoo\\custom\\school_management\\document\\student_captures";

if (!fs.existsSync(DOC_DIR)) {
    fs.mkdirSync(DOC_DIR, { recursive: true });
}

function log(msg) {
    process.stdout.write(`[${new Date().toISOString()}] ${msg}\n`);
}

const PAGES = [
    { name: "01_student_dashboard", actionId: 198, label: "01. Student Dashboard" },
    { name: "02_student_schedule", actionId: 850, label: "02. University Schedule" },
    { name: "03_my_classes", actionId: 836, label: "03. My Classes (Kanban)" },
    { name: "04_course_registration", actionId: 920, label: "04. Course Registration (Add/Drop)" },
    { name: "05_my_curriculum", actionId: 894, label: "05. My Curriculum" },
    { name: "06_my_assignments", actionId: 239, label: "06. My Assignments (Responsive Grid)" },
    { name: "07_my_submissions", actionId: 240, label: "07. My Submissions (Columns)" },
    { name: "08_attendance_history", actionId: 842, label: "08. Attendance History (Kanban)" },
    { name: "09_my_transcript", actionId: 238, label: "09. Academic Transcript" },
    { name: "10_my_report_cards", actionId: 237, label: "10. Semester Report Cards" },
    { name: "11_tuition_and_fees", actionId: 200, label: "11. Tuition & Fees" },
    { name: "12_service_requests", actionId: 924, label: "12. Student Service Requests" },
    { name: "13_profile_change_requests", actionId: 922, label: "13. Profile Change Requests" },
    { name: "14_course_evaluations", actionId: 926, label: "14. Course & Lecturer Evaluations" },
    { name: "15_student_profile_list", actionId: 235, label: "15. Student Profile (List)" }
];

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
    log(`Student Session ID: ${sessionId}`);

    const chromePath = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
    log("Launching Chrome...");
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
    if (!pageTarget) throw new Error("No page target found after retries");

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
        await new Promise(r => setTimeout(r, 4000));

        // Iterate through all actions
        for (const page of PAGES) {
            log(`Loading ${page.label} (Action ID: ${page.actionId})...`);
            const navRes = await sendCmd("Runtime.evaluate", {
                expression: `(async () => {
                    try {
                        const res = await odoo.__WOWL_DEBUG__.root.env.services.action.doAction(${page.actionId}, { clearBreadcrumbs: true });
                        return "OK: " + JSON.stringify(res || {});
                    } catch (e) {
                        return "ERR: " + e.message;
                    }
                })()`,
                awaitPromise: true,
                returnByValue: true
            });
            log(`  -> Nav status: ${navRes.result?.value}`);

            await new Promise(r => setTimeout(r, 2500));

            const check = await sendCmd("Runtime.evaluate", {
                expression: `(() => {
                    const cards = document.querySelectorAll('.o_kanban_record, .o_data_row').length;
                    const title = document.querySelector('.o_breadcrumb, .breadcrumb')?.innerText || document.title;
                    const err = document.querySelector('.o_error_dialog, .modal-title')?.innerText || '';
                    return { cards, title: title.replace(/\\n/g, ' '), err };
                })()`,
                returnByValue: true
            });
            const info = check.result?.value || {};
            log(`  -> Breadcrumb/Title: "${info.title}", Count: ${info.cards}, Alert: ${info.err || 'None'}`);

            await sendCmd("Emulation.setDeviceMetricsOverride", {
                width: 1920,
                height: 1080,
                deviceScaleFactor: 1,
                mobile: false
            });
            await new Promise(r => setTimeout(r, 300));

            const screenshot = await sendCmd("Page.captureScreenshot", {
                format: "png",
                clip: { x: 0, y: 0, width: 1920, height: 1080, scale: 1 }
            });

            const docFile = path.join(DOC_DIR, `${page.name}.png`);
            const artFile = path.join(ARTIFACT_DIR, `${page.name}.png`);
            const buf = Buffer.from(screenshot.data, "base64");
            fs.writeFileSync(docFile, buf);
            fs.writeFileSync(artFile, buf);
            log(`  -> Saved ${page.name}.png (${buf.length} bytes)`);
        }

        // 16. Student Profile Form View
        log("Loading Student Profile Form (Hannah Abbott, ID: 6)...");
        await sendCmd("Runtime.evaluate", {
            expression: `(async () => {
                await odoo.__WOWL_DEBUG__.root.env.services.action.doAction({
                    type: 'ir.actions.act_window',
                    res_model: 'university.student',
                    res_id: 6,
                    views: [[false, 'form']],
                    view_mode: 'form',
                    target: 'current'
                }, { clearBreadcrumbs: true });
            })()`,
            awaitPromise: true,
            returnByValue: true
        });
        await new Promise(r => setTimeout(r, 2500));
        const profFormShot = await sendCmd("Page.captureScreenshot", {
            format: "png",
            clip: { x: 0, y: 0, width: 1920, height: 1080, scale: 1 }
        });
        const docForm = path.join(DOC_DIR, `16_student_profile_form.png`);
        const artForm = path.join(ARTIFACT_DIR, `16_student_profile_form.png`);
        fs.writeFileSync(docForm, Buffer.from(profFormShot.data, "base64"));
        fs.writeFileSync(artForm, Buffer.from(profFormShot.data, "base64"));
        log("  -> Saved 16_student_profile_form.png");

        // 17. Online Tuition Payment Wizard (Modal Dialog)
        log("Opening Online Tuition Payment Wizard modal...");
        await sendCmd("Runtime.evaluate", {
            expression: `(async () => {
                await odoo.__WOWL_DEBUG__.root.env.services.action.doAction({
                    type: 'ir.actions.act_window',
                    res_model: 'university.fee.payment.wizard',
                    views: [[false, 'form']],
                    view_mode: 'form',
                    target: 'new',
                    context: { default_student_id: 6 }
                });
            })()`,
            awaitPromise: true,
            returnByValue: true
        });
        await new Promise(r => setTimeout(r, 2500));
        const wizardShot = await sendCmd("Page.captureScreenshot", {
            format: "png",
            clip: { x: 0, y: 0, width: 1920, height: 1080, scale: 1 }
        });
        const docWiz = path.join(DOC_DIR, `17_online_tuition_payment_wizard.png`);
        const artWiz = path.join(ARTIFACT_DIR, `17_online_tuition_payment_wizard.png`);
        fs.writeFileSync(docWiz, Buffer.from(wizardShot.data, "base64"));
        fs.writeFileSync(artWiz, Buffer.from(wizardShot.data, "base64"));
        log("  -> Saved 17_online_tuition_payment_wizard.png");

        ws.close();
        log("ALL 17 STUDENT PAGES CAPTURED SUCCESSFULLY!");
    } finally {
        chromeProc.kill();
    }
}

main().catch(err => {
    console.error("Capture script failed:", err);
    process.exit(1);
});
