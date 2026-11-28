const { spawn } = require('child_process');

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
    const chromeProc = spawn('C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe', [
        '--headless=new', '--remote-debugging-port=9252', '--disable-gpu', 'about:blank'
    ]);
    await new Promise(r => setTimeout(r, 2000));
    const targetsRes = await fetch('http://localhost:9252/json');
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
    await send('Network.setCookie', { name: 'session_id', value: sessionId, domain: 'localhost', path: '/' });
    await send('Page.navigate', { url: 'http://localhost:8070/odoo' });
    for (let i = 0; i < 20; i++) {
        await new Promise(r => setTimeout(r, 1000));
        const check = await send('Runtime.evaluate', {
            expression: 'Boolean(window.odoo?.__WOWL_DEBUG__?.root?.env?.services?.menu)',
            returnByValue: true
        });
        if (check.result?.value) break;
    }
    const res = await send('Runtime.evaluate', {
        expression: `(() => {
            const menuService = odoo.__WOWL_DEBUG__.root.env.services.menu;
            const menus = menuService.getAll();
            return Object.values(menus)
                .filter(m => m.name && m.name.toLowerCase().includes('profile'))
                .map(m => ({ id: m.id, name: m.name, xmlid: m.xmlid, parent: m.parents, appID: m.appID }));
        })()`,
        returnByValue: true
    });
    console.log('Profile menus in browser:\n', JSON.stringify(res.result?.value, null, 2));

    const schoolAppMenus = await send('Runtime.evaluate', {
        expression: `(() => {
            const menuService = odoo.__WOWL_DEBUG__.root.env.services.menu;
            const apps = menuService.getApps();
            const schoolApp = apps.find(a => a.xmlid === 'school_management.menu_school_root' || a.name.includes('Harvard'));
            const submenus = menuService.getMenuAsTree(schoolApp.id);
            return {
                app: schoolApp.name,
                children: submenus.childrenTree?.map(c => ({ id: c.id, name: c.name, xmlid: c.xmlid }))
            };
        })()`,
        returnByValue: true
    });
    console.log('School App submenus in browser:\n', JSON.stringify(schoolAppMenus.result?.value, null, 2));

    ws.close();
    chromeProc.kill();
}
test().catch(console.error);
