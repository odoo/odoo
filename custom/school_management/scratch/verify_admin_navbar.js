const { spawn } = require('child_process');
const fs = require('fs');

async function testNavbar() {
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
        '--headless=new', '--remote-debugging-port=9251', '--disable-gpu', '--window-size=1920,1080', 'about:blank'
    ]);
    await new Promise(r => setTimeout(r, 2000));
    const targetsRes = await fetch('http://localhost:9251/json');
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

    await send('Page.navigate', { url: 'http://localhost:8070/odoo' });
    for (let i = 0; i < 20; i++) {
        await new Promise(r => setTimeout(r, 1000));
        const check = await send('Runtime.evaluate', {
            expression: 'Boolean(window.odoo?.__WOWL_DEBUG__?.root?.env?.services?.menu)',
            returnByValue: true
        });
        if (check.result?.value) break;
    }

    // Switch to school app menu
    await send('Runtime.evaluate', {
        expression: `(async () => {
            const menuService = odoo.__WOWL_DEBUG__.root.env.services.menu;
            const apps = menuService.getApps();
            const schoolApp = apps.find(a => a.xmlid === 'school_management.menu_school_root' || a.name.includes('Harvard'));
            if (schoolApp) {
                await menuService.selectMenu(schoolApp);
            }
        })()`,
        awaitPromise: true,
        returnByValue: true
    });

    await new Promise(r => setTimeout(r, 4000));

    const navItems = await send('Runtime.evaluate', {
        expression: `(() => {
            const sections = Array.from(document.querySelectorAll('.o_menu_sections > *'))
                .map(el => el.innerText.trim()).filter(Boolean);
            const allNavText = document.querySelector('.o_main_navbar')?.innerText?.trim()?.replace(/\\n+/g, ' | ');
            return { sections, allNavText };
        })()`,
        returnByValue: true
    });
    console.log("Navbar inspection in Harvard University app:\n", JSON.stringify(navItems.result?.value, null, 2));

    const ss = await send('Page.captureScreenshot');
    fs.writeFileSync('C:/Odoo/odoo/custom/school_management/scratch/verify_admin_navbar.png', Buffer.from(ss.data, 'base64'));

    ws.close();
    chromeProc.kill();
}
testNavbar().catch(console.error);
