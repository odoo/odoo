const { spawn } = require('child_process');
const fs = require('fs');

async function check() {
    const authResp = await fetch('http://localhost:8069/web/session/authenticate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ jsonrpc: '2.0', params: { db: 'odoo', login: 'admin', password: 'admin' } })
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

    const chromeProc = spawn('C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe', [
        '--headless=new', '--remote-debugging-port=9247', '--disable-gpu', '--window-size=1920,1080', 'about:blank'
    ]);
    await new Promise(r => setTimeout(r, 2000));
    const targetsRes = await fetch('http://localhost:9247/json');
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

    await send('Page.navigate', { url: 'http://localhost:8069/odoo' });
    for (let i = 0; i < 20; i++) {
        await new Promise(r => setTimeout(r, 1000));
        const check = await send('Runtime.evaluate', {
            expression: 'Boolean(window.odoo?.__WOWL_DEBUG__?.root?.env?.services?.action)',
            returnByValue: true
        });
        if (check.result?.value) break;
    }

    const actResult = await send('Runtime.evaluate', {
        expression: `(async () => {
            const actionService = odoo.__WOWL_DEBUG__.root.env.services.action;
            return await actionService.doAction('school_management.action_university_timeslot');
        })()`,
        awaitPromise: true,
        returnByValue: true
    });
    console.log('Timeslot Kanban doAction:', actResult);

    await new Promise(r => setTimeout(r, 3000));
    const ss = await send('Page.captureScreenshot');
    fs.writeFileSync('C:/Odoo/odoo/custom/school_management/scratch/timeslot_kanban_view.png', Buffer.from(ss.data, 'base64'));
    
    const cpHTML = await send('Runtime.evaluate', {
        expression: 'document.querySelector(".o_control_panel") ? document.querySelector(".o_control_panel").outerHTML : "NO CP"',
        returnByValue: true
    });
    console.log('CP HTML length:', cpHTML.result?.value?.length);
    fs.writeFileSync('C:/Odoo/odoo/custom/school_management/scratch/cp_kanban.html', cpHTML.result?.value || '');

    ws.close();
    chromeProc.kill();
}
check().catch(console.error);
