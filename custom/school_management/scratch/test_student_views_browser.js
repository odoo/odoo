const { spawn } = require('child_process');

async function testViews() {
    console.log("Authenticating as admin...");
    const authResp = await fetch("http://localhost:8070/web/session/authenticate", {
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
    const chromeProc = spawn(chromePath, [
        "--headless=new",
        "--remote-debugging-port=9227",
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
            const targetsRes = await fetch("http://localhost:9227/json");
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
        const errorsCaught = [];

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.method === "Runtime.consoleAPICalled" && data.params.type === "error") {
                const msg = data.params.args.map(a => a.value || a.description || "").join(" ");
                console.log("[CONSOLE ERROR]", msg);
                errorsCaught.push(msg);
            }
            if (data.method === "Runtime.exceptionThrown") {
                const details = data.params.exceptionDetails;
                const excMsg = details.exception?.description || details.text || "";
                console.log("[RUNTIME EXCEPTION]", excMsg);
                errorsCaught.push(excMsg);
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

        console.log("Navigating to Odoo web client...");
        await sendCmd("Page.navigate", { url: "http://localhost:8070/odoo" });
        await new Promise(r => setTimeout(r, 5000));

        // Test Action 181 (Students - Kanban)
        console.log("\n--- Testing Action 181: Students (Kanban) ---");
        let res = await sendCmd("Runtime.evaluate", {
            expression: `(async () => {
                const actionService = odoo.__WOWL_DEBUG__.root.env.services.action;
                return await actionService.doAction(181, { clearBreadcrumbs: true });
            })()`,
            awaitPromise: true,
            returnByValue: true
        });
        await new Promise(r => setTimeout(r, 3000));

        // Switch to List view
        console.log("\n--- Testing Action 181: Students (Switch to List) ---");
        res = await sendCmd("Runtime.evaluate", {
            expression: `(async () => {
                const actionService = odoo.__WOWL_DEBUG__.root.env.services.action;
                return await actionService.switchView("list");
            })()`,
            awaitPromise: true,
            returnByValue: true
        });
        await new Promise(r => setTimeout(r, 3000));

        // Open Student Form (ID 1)
        console.log("\n--- Testing Student Form (res_id: 1) ---");
        res = await sendCmd("Runtime.evaluate", {
            expression: `(async () => {
                const actionService = odoo.__WOWL_DEBUG__.root.env.services.action;
                return await actionService.doAction({
                    type: "ir.actions.act_window",
                    res_model: "university.student",
                    res_id: 1,
                    views: [[false, "form"]],
                    view_mode: "form",
                    target: "current"
                }, { clearBreadcrumbs: true });
            })()`,
            awaitPromise: true,
            returnByValue: true
        });
        await new Promise(r => setTimeout(r, 3000));

        // Click all tabs on Student Form!
        console.log("\n--- Clicking through all tabs on Student Form ---");
        const tabNames = ['overview_tab', 'enrollments_tab', 'my_curriculum_tab', 'fees_tab', 'academic_results_tab', 'submissions_tab', 'advising_tab', 'notes_tab'];
        for (const t of tabNames) {
            console.log(`Clicking tab ${t}...`);
            await sendCmd("Runtime.evaluate", {
                expression: `(() => {
                    const el = document.querySelector('a[name="${t}"]') || document.querySelector('.nav-link[name="${t}"]');
                    if (el) el.click();
                    return !!el;
                })()`,
                returnByValue: true
            });
            await new Promise(r => setTimeout(r, 1000));
        }

        // Test Student login
        console.log("\n--- Testing as Student login ---");
        await sendCmd("Page.navigate", { url: "http://localhost:8070/web/session/logout" });
        await new Promise(r => setTimeout(r, 2000));

        const studentAuthResp = await fetch("http://localhost:8070/web/session/authenticate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                jsonrpc: "2.0",
                params: { db: "odoo", login: "student", password: "1234" }
            })
        });
        const studentCookies = studentAuthResp.headers.getSetCookie ? studentAuthResp.headers.getSetCookie() : [studentAuthResp.headers.get('set-cookie')];
        let studentSessionId = null;
        for (const c of studentCookies) {
            if (!c) continue;
            for (const part of c.split(';')) {
                if (part.trim().startsWith('session_id=')) {
                    studentSessionId = part.trim().split('=')[1];
                    break;
                }
            }
        }
        await sendCmd("Network.setCookie", {
            name: "session_id",
            value: studentSessionId,
            domain: "localhost",
            path: "/"
        });
        await sendCmd("Page.navigate", { url: "http://localhost:8070/odoo" });
        await new Promise(r => setTimeout(r, 5000));

        // Open Student Profile (Action 235)
        console.log("\n--- As Student: Opening Action 235 (My Profile) ---");
        await sendCmd("Runtime.evaluate", {
            expression: `(async () => {
                const actionService = odoo.__WOWL_DEBUG__.root.env.services.action;
                return await actionService.doAction(235, { clearBreadcrumbs: true });
            })()`,
            awaitPromise: true,
            returnByValue: true
        });
        await new Promise(r => setTimeout(r, 3000));

        // Click student tabs
        for (const t of tabNames) {
            console.log(`Student clicking tab ${t}...`);
            await sendCmd("Runtime.evaluate", {
                expression: `(() => {
                    const el = document.querySelector('a[name="${t}"]') || document.querySelector('.nav-link[name="${t}"]');
                    if (el) el.click();
                    return !!el;
                })()`,
                returnByValue: true
            });
            await new Promise(r => setTimeout(r, 1000));
        }

        console.log("\n================ SUMMARY ================");
        console.log(`Total errors caught: ${errorsCaught.length}`);
        for (const e of errorsCaught) {
            console.log(" - ", e);
        }

        ws.close();
    } finally {
        chromeProc.kill();
    }
}

testViews().catch(console.error);
