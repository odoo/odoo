const { spawn } = require('child_process');
const fs = require('fs');

async function test() {
    console.log("Authenticating teacher session...");
    const authResp = await fetch('http://localhost:8070/web/session/authenticate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ jsonrpc: '2.0', params: { db: 'odoo', login: 'teacher', password: '1234' } })
    });
    const authData = await authResp.json();
    console.log("Teacher logged in:", authData.result?.name || "OK");

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
        '--headless=new', '--remote-debugging-port=9241', '--disable-gpu', '--window-size=1920,1080', 'about:blank'
    ]);
    await new Promise(r => setTimeout(r, 2000));
    const targetsRes = await fetch('http://localhost:9241/json');
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
    
    console.log("Navigating directly to action-193 as Teacher (simulating user's exact flow)...");
    await send('Page.navigate', { url: 'http://localhost:8070/odoo/action-193' });
    await new Promise(r => setTimeout(r, 7000));

    // Inspect if Teacher Dashboard loaded or was redirected
    const check193 = await send('Runtime.evaluate', {
        expression: `(() => {
            const hasTeacherDash = Boolean(document.querySelector('.o_teacher_dashboard'));
            const hasExecDash = Boolean(document.querySelector('.o_exec_portal_root'));
            const text = document.body.innerText;
            return {
                hasTeacherDash,
                hasExecDash,
                url: window.location.href,
                containsExams: text.includes('Exams & Marksheets'),
                containsTeachingLoad: text.includes('TEACHING LOAD'),
                snippet: text.slice(0, 300)
            };
        })()`,
        returnByValue: true
    });
    console.log("Result at action-193:\n", JSON.stringify(check193.result?.value, null, 2));

    const ss1 = await send('Page.captureScreenshot');
    fs.writeFileSync('custom/school_management/scratch/teacher_action193_result.png', Buffer.from(ss1.data, 'base64'));

    ws.close();
    chromeProc.kill();
}
test().catch(console.error);
