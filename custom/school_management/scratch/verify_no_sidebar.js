const { spawn } = require('child_process');
const fs = require('fs');

async function test() {
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
    console.log('Session ID:', sessionId);

    const chromePath = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
    const chromeProc = spawn(chromePath, [
        '--headless=new',
        '--remote-debugging-port=9222',
        '--disable-extensions',
        '--disable-gpu',
        '--remote-allow-origins=*',
        '--window-size=1920,1080',
        'about:blank'
    ]);

    let pageTarget = null;
    for (let i = 0; i < 15; i++) {
        await new Promise(r => setTimeout(r, 600));
        try {
            const targetsRes = await fetch('http://localhost:9222/json');
            const targets = await targetsRes.json();
            pageTarget = targets.find(t => t.type === 'page' && !t.url.startsWith('chrome-extension'));
            if (pageTarget) break;
        } catch {}
    }

    try {
        const ws = new WebSocket(pageTarget.webSocketDebuggerUrl);
        await new Promise((resolve, reject) => { ws.onopen = resolve; ws.onerror = reject; });

        let idCounter = 1;
        const pending = new Map();
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
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

        await sendCmd('Page.enable');
        await sendCmd('Network.enable');
        await sendCmd('Runtime.enable');

        if (sessionId) {
            await sendCmd('Network.setCookie', {
                name: 'session_id',
                value: sessionId,
                domain: 'localhost',
                path: '/'
            });
        }

        console.log('Navigating to dashboard action-193...');
        await sendCmd('Page.navigate', { url: 'http://localhost:8070/odoo?menu_id=90&action=193' });
        await new Promise(r => setTimeout(r, 6000));

        const checkRes = await sendCmd('Runtime.evaluate', {
            expression: `({
                hasExecSidebar: !!document.querySelector('.o_exec_sidebar'),
                hasContainer: !!document.querySelector('.o_executive_dashboard_container'),
                containerWidth: document.querySelector('.o_executive_dashboard_container')?.offsetWidth,
                errorDialog: document.querySelector('.o_error_dialog')?.innerText || 'NO_ERROR'
            })`,
            returnByValue: true
        });
        console.log('Dashboard Check Result:', checkRes.result?.value);

        const screenshot = await sendCmd('Page.captureScreenshot', { format: 'png' });
        fs.writeFileSync('c:\\Odoo\\odoo\\custom\\school_management\\document\\admin_dashboard_fullpage.png', Buffer.from(screenshot.data, 'base64'));
        console.log('Saved admin_dashboard_fullpage.png without sidebar!');

        ws.close();
    } finally {
        chromeProc.kill();
    }
}
test().catch(console.error);
