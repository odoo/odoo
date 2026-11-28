const { spawn } = require('child_process');

async function testTeacher() {
    console.log("Authenticating as teacher...");
    const authResp = await fetch("http://localhost:8070/web/session/authenticate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            jsonrpc: "2.0",
            params: { db: "odoo", login: "teacher", password: "1234" }
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
    console.log("Teacher Session ID:", sessionId);

    const chromePath = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
    const chromeProc = spawn(chromePath, [
        "--headless=new",
        "--remote-debugging-port=9228",
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
            const targetsRes = await fetch("http://localhost:9228/json");
            const targets = await targetsRes.json();
            pageTarget = targets.find(t => t.type === 'page' && !t.url.startsWith('chrome-extension'));
            if (pageTarget) break;
        } catch {}
    }
    if (!pageTarget) throw new Error("No page target");

    try {
        const ws = new WebSocket(pageTarget.webSocketDebuggerUrl);
        await new Promise((resolve, reject) => {
            ws.onopen = resolve;
            ws.onerror = reject;
        });

        let idCounter = 1;
        const pending = new Map();
        const errors = [];

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.method === "Runtime.consoleAPICalled") {
                const type = data.params.type;
                const msg = data.params.args.map(a => a.value || a.description || "").join(" ");
                if (type === "error") {
                    console.log("[CONSOLE ERROR]", msg);
                    errors.push(msg);
                }
            }
            if (data.method === "Runtime.exceptionThrown") {
                const details = data.params.exceptionDetails;
                const text = details.exception?.description || details.text || "";
                console.log("[EXCEPTION THROWN]", text);
                errors.push(text);
            }
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

        console.log("Navigating to Odoo web client as teacher...");
        await sendCmd("Page.navigate", { url: "http://localhost:8070/odoo" });
        await new Promise(r => setTimeout(r, 6000));

        // Let's see what menus or actions are available to teacher
        console.log("Checking current action / app...");
        let info = await sendCmd("Runtime.evaluate", {
            expression: `(() => {
                const env = odoo.__WOWL_DEBUG__.root.env;
                const action = env.services.action.currentController?.action;
                const menu = env.services.menu.getAll();
                return {
                    currentAction: action ? { id: action.id, xml_id: action.xml_id, name: action.name, res_model: action.res_model } : null,
                    menuCount: Object.keys(menu).length,
                    menus: Object.values(menu).map(m => ({ id: m.id, name: m.name, actionID: m.actionID, xmlid: m.xmlid }))
                };
            })()`,
            returnByValue: true
        });
        console.log("Current state:", JSON.stringify(info.result?.value?.currentAction, null, 2));
        console.log("Menus count:", info.result?.value?.menuCount);
        const menus = info.result?.value?.menus || [];
        for (const m of menus.filter(x => x.name.toLowerCase().includes('student') || x.name.toLowerCase().includes('school'))) {
            console.log("  Matching Menu:", m);
        }

        // Test opening Students action (181) as Teacher
        console.log("\n--- Opening Students Action (181) as Teacher ---");
        let actRes = await sendCmd("Runtime.evaluate", {
            expression: `(async () => {
                try {
                    const actionService = odoo.__WOWL_DEBUG__.root.env.services.action;
                    return await actionService.doAction(181, { clearBreadcrumbs: true });
                } catch (e) {
                    return { error: e.stack || e.message };
                }
            })()`,
            awaitPromise: true,
            returnByValue: true
        });
        console.log("Action 181 result:", JSON.stringify(actRes.result?.value));
        await new Promise(r => setTimeout(r, 3000));

        // Check if Kanban loaded or had errors
        let viewCheck = await sendCmd("Runtime.evaluate", {
            expression: `(() => {
                return {
                    records: document.querySelectorAll('.o_kanban_record').length,
                    errorDialog: document.querySelector('.o_error_dialog, .modal-title')?.innerText || null
                };
            })()`,
            returnByValue: true
        });
        console.log("Kanban check:", viewCheck.result?.value);

        // Switch to List view
        console.log("\n--- Switching to List view as Teacher ---");
        let listRes = await sendCmd("Runtime.evaluate", {
            expression: `(async () => {
                try {
                    const actionService = odoo.__WOWL_DEBUG__.root.env.services.action;
                    return await actionService.switchView("list");
                } catch (e) {
                    return { error: e.stack || e.message };
                }
            })()`,
            awaitPromise: true,
            returnByValue: true
        });
        console.log("List switch result:", JSON.stringify(listRes.result?.value));
        await new Promise(r => setTimeout(r, 3000));

        // Open Student Form (res_id 1) as Teacher
        console.log("\n--- Opening Student Form (res_id: 6) as Teacher ---");
        let formRes = await sendCmd("Runtime.evaluate", {
            expression: `(async () => {
                try {
                    const actionService = odoo.__WOWL_DEBUG__.root.env.services.action;
                    return await actionService.doAction({
                        type: "ir.actions.act_window",
                        res_model: "university.student",
                        res_id: 6,
                        views: [[false, "form"]],
                        view_mode: "form",
                        target: "current"
                    }, { clearBreadcrumbs: true });
                } catch (e) {
                    return { error: e.stack || e.message };
                }
            })()`,
            awaitPromise: true,
            returnByValue: true
        });
        console.log("Form open result:", JSON.stringify(formRes.result?.value));
        await new Promise(r => setTimeout(r, 3000));

        // Click through tabs as Teacher
        const tabNames = ['overview_tab', 'enrollments_tab', 'my_curriculum_tab', 'fees_tab', 'academic_results_tab', 'submissions_tab', 'advising_tab', 'notes_tab'];
        for (const t of tabNames) {
            console.log(`Teacher clicking tab ${t}...`);
            let clickRes = await sendCmd("Runtime.evaluate", {
                expression: `(() => {
                    const el = document.querySelector('a[name="${t}"]') || document.querySelector('.nav-link[name="${t}"]');
                    if (el) el.click();
                    const err = document.querySelector('.o_error_dialog, .modal-title')?.innerText || null;
                    return { found: !!el, err };
                })()`,
                returnByValue: true
            });
            console.log(`  -> tab ${t}:`, clickRes.result?.value);
            await new Promise(r => setTimeout(r, 1500));
        }

        // Test clicking action_view_exam_scores button on student form
        console.log("\n--- Testing Result of Exam and Quiz button on Student Form as Teacher ---");
        let btnRes = await sendCmd("Runtime.evaluate", {
            expression: `(async () => {
                try {
                    const btn = document.querySelector('button[name=\"action_view_exam_scores\"]');
                    if (btn) {
                        btn.click();
                        return { clicked: true };
                    }
                    return { clicked: false, msg: "button not found" };
                } catch (e) {
                    return { error: e.stack || e.message };
                }
            })()`,
            awaitPromise: true,
            returnByValue: true
        });
        console.log("Button click result:", btnRes.result?.value);
        await new Promise(r => setTimeout(r, 3000));

        console.log("\n================ SUMMARY ================");
        console.log(`Total errors caught: ${errors.length}`);
        for (const e of errors) {
            console.log(" - ", e);
        }

        ws.close();
    } finally {
        chromeProc.kill();
    }
}

testTeacher().catch(console.error);
