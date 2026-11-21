const { spawn } = require('child_process');

async function testViews() {
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

    const chromePath = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
    const chromeProc = spawn(chromePath, [
        "--headless=new",
        "--remote-debugging-port=9231",
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
            const targetsRes = await fetch("http://localhost:9231/json");
            const targets = await targetsRes.json();
            pageTarget = targets.find(t => t.type === 'page' && !t.url.startsWith('chrome-extension'));
            if (pageTarget) break;
        } catch {}
    }

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
            if (data.method === "Runtime.consoleAPICalled" && data.params.type === "error") {
                const msg = data.params.args.map(a => a.value || a.description || "").join(" ");
                console.log("[CONSOLE ERROR]", msg);
                errors.push(msg);
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

        await sendCmd("Page.navigate", { url: "http://localhost:8070/odoo" });
        await new Promise(r => setTimeout(r, 5000));

        // Test Timetable Slots Action (action_university_timetable_slot)
        console.log("\n--- Opening Timetable Slots Action with 'This Week' filter ---");
        let ttRes = await sendCmd("Runtime.evaluate", {
            expression: `(async () => {
                try {
                    const actionService = odoo.__WOWL_DEBUG__.root.env.services.action;
                    return await actionService.doAction("school_management.action_university_timetable_slot", {
                        additionalContext: { search_default_filter_this_week: 1 },
                        clearBreadcrumbs: true
                    });
                } catch (e) {
                    return { error: e.stack || e.message };
                }
            })()`,
            awaitPromise: true,
            returnByValue: true
        });
        console.log("Timetable Action result:", ttRes.result?.value);
        await new Promise(r => setTimeout(r, 3000));

        // Test Assignments Action with "Due This Week" filter
        console.log("\n--- Opening Assignments Action with 'Due This Week' filter ---");
        let asRes = await sendCmd("Runtime.evaluate", {
            expression: `(async () => {
                try {
                    const actionService = odoo.__WOWL_DEBUG__.root.env.services.action;
                    return await actionService.doAction("school_management.action_university_assignment", {
                        additionalContext: { search_default_due_this_week: 1 },
                        clearBreadcrumbs: true
                    });
                } catch (e) {
                    return { error: e.stack || e.message };
                }
            })()`,
            awaitPromise: true,
            returnByValue: true
        });
        console.log("Assignments Action result:", asRes.result?.value);
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

testViews().catch(console.error);
