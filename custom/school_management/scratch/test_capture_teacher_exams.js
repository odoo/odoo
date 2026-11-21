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
        '--headless=new', '--remote-debugging-port=9242', '--disable-gpu', '--window-size=1920,1080', 'about:blank'
    ]);
    await new Promise(r => setTimeout(r, 2000));
    const targetsRes = await fetch('http://localhost:9242/json');
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
    
    await send('Page.navigate', { url: 'http://localhost:8070/odoo/action-212' });
    await new Promise(r => setTimeout(r, 6000));

    // Click Exams tab
    await send('Runtime.evaluate', {
        expression: `(() => {
            const btns = Array.from(document.querySelectorAll('button'));
            const examBtn = btns.find(b => b.innerText.includes('Exams & Marksheets'));
            if (examBtn) examBtn.click();
        })()`
    });
    await new Promise(r => setTimeout(r, 2000));

    const ss = await send('Page.captureScreenshot');
    fs.writeFileSync('C:/Users/Rith2/.gemini/antigravity-acp/brain/78b4311f-52e2-48ba-b5c3-a1f375fd9f6c/teacher_exams_tab_verified.png', Buffer.from(ss.data, 'base64'));
    console.log("Teacher Exams tab screenshot saved!");

    ws.close();
    chromeProc.kill();
}
test().catch(console.error);
