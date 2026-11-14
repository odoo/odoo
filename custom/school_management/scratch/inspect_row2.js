const { spawn } = require('child_process');

async function run() {
    const chromeProc = spawn('C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe', [
        '--headless=new', '--remote-debugging-port=9250', '--disable-gpu', '--window-size=1680,1050', 'about:blank'
    ]);
    await new Promise(r => setTimeout(r, 1500));
    const targetsRes = await fetch('http://localhost:9250/json');
    const targets = await targetsRes.json();
    const ws = new WebSocket(targets[0].webSocketDebuggerUrl);
    await new Promise(r => ws.onopen = r);
    let id = 1;
    function send(m, p={}) {
        return new Promise(res => {
            const cur = id++;
            const h = (e) => {
                const d = JSON.parse(e.data);
                if (d.id === cur) { ws.removeEventListener('message', h); res(d.result); }
            };
            ws.addEventListener('message', h);
            ws.send(JSON.stringify({ id: cur, method: m, params: p }));
        });
    }
    await send('Network.enable');
    const authResp = await fetch('http://localhost:8070/web/session/authenticate', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ jsonrpc: '2.0', params: { db: 'odoo', login: 'student', password: '1234' } })
    });
    const setCookies = authResp.headers.getSetCookie ? authResp.headers.getSetCookie() : [authResp.headers.get('set-cookie')];
    let sess = '';
    for (const c of setCookies) {
        if (!c) continue;
        for (const p of c.split(';')) if (p.trim().startsWith('session_id=')) sess = p.trim().split('=')[1];
    }
    await send('Network.setCookie', { name: 'session_id', value: sess, domain: 'localhost', path: '/' });
    await send('Page.navigate', { url: 'http://localhost:8070/odoo/action-school_management.action_university_schedule_view' });
    for (let i = 0; i < 30; i++) {
        await new Promise(r => setTimeout(r, 500));
        const c = await send('Runtime.evaluate', {
            expression: `Boolean(document.querySelector('.o_schedule_top_bar'))`
        });
        if (c.result?.value) break;
    }
    const evalRes = await send('Runtime.evaluate', {
        expression: `(() => {
            const row2 = document.querySelector('.o_schedule_top_bar .border-top');
            const left = row2 ? row2.children[0] : null;
            if (!left) return 'left not found';
            return {
                row2Width: row2.getBoundingClientRect().width,
                leftWidth: left.getBoundingClientRect().width,
                children: Array.from(left.children).map(c => ({
                    tag: c.tagName,
                    cls: c.className,
                    text: c.innerText.trim(),
                    w: c.getBoundingClientRect().width,
                    top: c.getBoundingClientRect().top
                }))
            };
        })()`,
        returnByValue: true
    });
    console.log(JSON.stringify(evalRes.result.value, null, 2));
    ws.close();
    chromeProc.kill();
}
run();
