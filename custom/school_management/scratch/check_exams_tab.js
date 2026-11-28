const fs = require('fs');
const { spawn } = require('child_process');

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
        '--headless=new', '--remote-debugging-port=9231', '--disable-gpu', '--window-size=1920,1080', 'about:blank'
    ]);
    await new Promise(r => setTimeout(r, 2000));
    const targetsRes = await fetch('http://localhost:9231/json');
    const targets = await targetsRes.json();
    const pageTarget = targets.find(t => t.type === 'page');
    const ws = new WebSocket(pageTarget.webSocketDebuggerUrl);
    await new Promise(r => { ws.onopen = r; });
    let id = 1;
    function send(method, params={}) {
        return new Promise((res, rej) => {
            const curId = id++;
            const handler = (msg) => {
                const d = JSON.parse(msg.data);
                if (d.id === curId) { ws.removeEventListener('message', handler); res(d.result); }
            };
            ws.addEventListener('message', handler);
            ws.send(JSON.stringify({ id: curId, method, params }));
        });
    }
    await send('Network.enable');
    await send('Page.enable');
    await send('Network.setCookie', { name: 'session_id', value: sessionId, domain: 'localhost', path: '/' });
    await send('Page.navigate', { url: 'http://localhost:8070/odoo?action=teacher_dashboard_shell' });
    await new Promise(r => setTimeout(r, 5000));
    const tabClick = await send('Runtime.evaluate', {
        expression: (() => {
            const btns = Array.from(document.querySelectorAll('button'));
            const examBtn = btns.find(b => b.innerText.includes('Exams & Marksheets') || b.innerText.includes('Exam Marksheets'));
            if (examBtn) { examBtn.click(); return 'CLICKED EXAM TAB'; }
            return 'EXAM TAB NOT FOUND';
        })(),
        returnByValue: true
    });
    console.log('Tab click:', tabClick.result?.value);
    await new Promise(r => setTimeout(r, 2000));
    const content = await send('Runtime.evaluate', {
        expression: 'document.querySelector(".o_teacher_dashboard") ? document.querySelector(".o_teacher_dashboard").innerText.slice(0, 1000) : "not found"',
        returnByValue: true
    });
    console.log('Dashboard content:\n', content.result?.value);
    const ss = await send('Page.captureScreenshot');
    fs.writeFileSync('C:/Odoo/odoo/custom/school_management/scratch/teacher_dash_exams.png', Buffer.from(ss.data, 'base64'));
    console.log('Saved screenshot to scratch/teacher_dash_exams.png');
    ws.close();
    chromeProc.kill();
}
test().catch(console.error);
