const { spawn } = require('child_process');
const fs = require('fs');

async function test() {
    const authResp = await fetch('http://localhost:8070/web/session/authenticate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ jsonrpc: '2.0', params: { db: 'odoo', login: 'student', password: '1234' } })
    });
    const setCookies = authResp.headers.getSetCookie ? authResp.headers.getSetCookie() : [authResp.headers.get('set-cookie')];
    let sessionId = null;
    for (const c of setCookies) {
        if (!c) continue;
        for (const part of c.split(';')) {
            if (part.trim().startsWith('session_id=')) sessionId = part.trim().split('=')[1];
        }
    }
    console.log('Session ID:', sessionId);
    const chrome = spawn('C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe', [
        '--headless=new',
        '--remote-debugging-port=9249',
        '--disable-extensions',
        '--disable-gpu',
        '--remote-allow-origins=*',
        '--window-size=1680,1050',
        'about:blank'
    ]);
    await new Promise(r => setTimeout(r, 1500));
    const targetsRes = await fetch('http://localhost:9249/json');
    const targets = await targetsRes.json();
    const pageTarget = targets.find(t => t.type === 'page');
    const ws = new WebSocket(pageTarget.webSocketDebuggerUrl);
    await new Promise(r => ws.onopen = r);
    let id = 1;
    const send = (method, params = {}) => new Promise((resolve, reject) => {
        const msgId = id++;
        const handler = (evt) => {
            const m = JSON.parse(evt.data);
            if (m.id === msgId) {
                ws.removeEventListener('message', handler);
                if (m.error) reject(m.error);
                else resolve(m.result);
            }
        };
        ws.addEventListener('message', handler);
        ws.send(JSON.stringify({ id: msgId, method, params }));
    });
    ws.addEventListener('message', evt => {
        const m = JSON.parse(evt.data);
        if (m.method === 'Runtime.consoleAPICalled') {
            console.log('[CONSOLE]', m.params.type, m.params.args.map(a => a.value || a.description).join(' '));
        } else if (m.method === 'Runtime.exceptionThrown') {
            console.log('[EXCEPTION]', JSON.stringify(m.params.exceptionDetails));
        }
    });
    await send('Runtime.enable');
    await send('Page.enable');
    await send('Network.enable');
    await send('Network.setCookie', { name: 'session_id', value: sessionId, domain: 'localhost', path: '/' });
    await send('Page.navigate', { url: 'http://localhost:8070/odoo/action-school_management.action_university_schedule_view' });
    for (let i = 0; i < 30; i++) {
        await new Promise(r => setTimeout(r, 500));
        const res = await send('Runtime.evaluate', { 
            expression: '({ title: document.title, hasSchedule: Boolean(document.querySelector(".o_university_schedule_wrapper")), len: document.body.innerHTML.length, text: document.body.innerText.substring(0, 100) })', 
            returnByValue: true 
        });
        console.log('Poll', i, res.result?.value);
        if (res.result?.value?.hasSchedule) break;
    }
    const screenshot = await send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync('C:\\Users\\Rith2\\.gemini\\antigravity\\brain\\04dd9293-b979-4b90-a61b-cd709d86fc01\\schedule_current_state.png', Buffer.from(screenshot.data, 'base64'));
    console.log('Saved screenshot successfully!');
    chrome.kill();
    process.exit(0);
}
test().catch(e => { console.error(e); process.exit(1); });
