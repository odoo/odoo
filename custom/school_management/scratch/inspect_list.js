const { spawn } = require('child_process');
const fs = require('fs');

async function inspectList() {
    const chromeProc = spawn('C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe', [
        '--headless=new', '--remote-debugging-port=9249', '--disable-gpu', '--window-size=1920,1080', 'about:blank'
    ]);
    await new Promise(r => setTimeout(r, 2000));
    const targetsRes = await fetch('http://localhost:9249/json');
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
    
    // Auth
    const authResp = await fetch('http://localhost:8070/web/session/authenticate', {
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
    await send('Network.setCookie', { name: 'session_id', value: sessionId, domain: 'localhost', path: '/' });

    await send('Page.navigate', { url: 'http://localhost:8070/odoo' });
    for (let i = 0; i < 20; i++) {
        await new Promise(r => setTimeout(r, 1000));
        const check = await send('Runtime.evaluate', {
            expression: 'Boolean(window.odoo?.__WOWL_DEBUG__?.root?.env?.services?.action)',
            returnByValue: true
        });
        if (check.result?.value) break;
    }

    await send('Runtime.evaluate', {
        expression: `(async () => {
            const actionService = odoo.__WOWL_DEBUG__.root.env.services.action;
            return await actionService.doAction(217, { viewType: 'list' });
        })()`,
        awaitPromise: true,
        returnByValue: true
    });
    await new Promise(r => setTimeout(r, 3000));

    const listInfo = await send('Runtime.evaluate', {
        expression: `(() => {
            const ths = Array.from(document.querySelectorAll('.o_list_table th')).map(th => th.innerText.trim());
            const rows = Array.from(document.querySelectorAll('.o_list_table tbody tr')).slice(0, 5).map(tr => tr.innerText.trim().replace(/\\n+/g, ' | '));
            return { ths, rows };
        })()`,
        returnByValue: true
    });
    console.log('List headers:', listInfo.result?.value?.ths);
    console.log('List rows sample:', listInfo.result?.value?.rows);

    ws.close();
    chromeProc.kill();
}
inspectList().catch(console.error);
