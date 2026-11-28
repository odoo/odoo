const { spawn } = require('child_process');
const fs = require('fs');

async function test() {
    const authResp = await fetch('http://localhost:8070/web/session/authenticate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ jsonrpc: '2.0', params: { db: 'odoo', login: 'teacher', password: '1234' } })
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
        '--headless=new', '--remote-debugging-port=9229', '--disable-gpu', '--window-size=1920,1080', 'about:blank'
    ]);
    await new Promise(r => setTimeout(r, 2000));
    const targetsRes = await fetch('http://localhost:9229/json');
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
    await send('Network.enable');
    await send('Page.enable');
    await send('Network.setCookie', { name: 'session_id', value: sessionId, domain: 'localhost', path: '/' });
    
    console.log("Navigating to /web#action=193...");
    await send('Page.navigate', { url: 'http://localhost:8070/web#action=193' });
    await new Promise(r => setTimeout(r, 6000));
    
    const res = await send('Runtime.evaluate', {
        expression: `(() => {
            const teacherDash = document.querySelector('.o_teacher_dashboard');
            const btns = Array.from(document.querySelectorAll('button')).map(b => b.innerText.replace(/\\s+/g, ' ').trim()).filter(Boolean);
            return {
                hasTeacherDashboard: Boolean(teacherDash),
                buttons: btns.slice(0, 15)
            };
        })()`,
        returnByValue: true
    });
    console.log('Result:', JSON.stringify(res.result?.value, null, 2));

    const ss = await send('Page.captureScreenshot');
    fs.writeFileSync('custom/school_management/scratch/teacher_action_193.png', Buffer.from(ss.data, 'base64'));
    console.log('Saved screenshot to custom/school_management/scratch/teacher_action_193.png');

    ws.close();
    chromeProc.kill();
}
test().catch(console.error);
