const { spawn } = require('child_process');
const fs = require('fs');

async function test() {
    const authResp = await fetch('http://localhost:8070/web/session/authenticate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ jsonrpc: '2.0', params: { db: 'odoo', login: 'admin', password: 'admin' } })
    });
    const authData = await authResp.json();
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

    const chromeProc = spawn('C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe', [
        '--headless=new', '--remote-debugging-port=9246', '--disable-gpu', '--window-size=1920,1080', 'about:blank'
    ]);
    await new Promise(r => setTimeout(r, 2000));
    const targetsRes = await fetch('http://localhost:9246/json');
    const targets = await targetsRes.json();
    const ws = new WebSocket(targets.find(t => t.type === 'page').webSocketDebuggerUrl);
    await new Promise(r => { ws.onopen = r; });
    let id = 1;
    function send(m, p={}) {
        return new Promise((res) => {
            const curId = id++;
            const h = (msg) => { const d = JSON.parse(msg.data); if (d.id === curId) { ws.removeEventListener('message', h); res(d.result); } };
            ws.addEventListener('message', h);
            ws.send(JSON.stringify({ id: curId, method: m, params: p }));
        });
    }

    await send('Runtime.enable');
    await send('Network.enable');
    await send('Page.enable');
    await send('Network.setCookie', { name: 'session_id', value: sessionId, domain: 'localhost', path: '/' });

    console.log("Navigating to http://localhost:8070/odoo ...");
    await send('Page.navigate', { url: 'http://localhost:8070/odoo' });
    
    // Poll until odoo is ready
    for (let i = 0; i < 20; i++) {
        await new Promise(r => setTimeout(r, 1000));
        const check = await send('Runtime.evaluate', {
            expression: `Boolean(window.odoo?.__WOWL_DEBUG__?.root?.env?.services?.action)`,
            returnByValue: true
        });
        if (check.result?.value) break;
    }

    console.log("Executing doAction for 217...");
    const actResult = await send('Runtime.evaluate', {
        expression: `(async () => {
            try {
                const actionService = odoo.__WOWL_DEBUG__.root.env.services.action;
                const res = await actionService.doAction(217);
                return { res };
            } catch (e) {
                return { error: e.message, stack: e.stack };
            }
        })()`,
        awaitPromise: true,
        returnByValue: true
    });
    console.log("doAction:", JSON.stringify(actResult.result?.value, null, 2));

    await new Promise(r => setTimeout(r, 4000));

    const checkDom = await send('Runtime.evaluate', {
        expression: `(() => {
            const cur = odoo.__WOWL_DEBUG__.root.env.services.action.currentController;
            return {
                actionName: cur?.action?.name,
                viewType: cur?.view?.type,
                viewMode: cur?.viewMode,
                bodySnippet: document.body.innerText.slice(0, 1000),
                actionManagerHTML: document.querySelector('.o_action_manager')?.innerHTML?.slice(0, 1000)
            };
        })()`,
        returnByValue: true
    });
    console.log("Current Controller & DOM:\n", JSON.stringify(checkDom.result?.value, null, 2));

    const ss = await send('Page.captureScreenshot');
    fs.writeFileSync('C:/Odoo/odoo/custom/school_management/scratch/timetable_gantt_verified.png', Buffer.from(ss.data, 'base64'));
    fs.copyFileSync('C:/Odoo/odoo/custom/school_management/scratch/timetable_gantt_verified.png', 'C:/Users/Rith2/.gemini/antigravity-acp/brain/78b4311f-52e2-48ba-b5c3-a1f375fd9f6c/timetable_gantt_verified.png');

    ws.close();
    chromeProc.kill();
}
test().catch(console.error);
