const { spawn } = require('child_process');
const fs = require('fs');

async function verify() {
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
        '--headless=new', '--remote-debugging-port=9250', '--disable-gpu', '--window-size=1920,1080', 'about:blank'
    ]);
    await new Promise(r => setTimeout(r, 2000));
    const targetsRes = await fetch('http://localhost:9250/json');
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
            expression: 'Boolean(window.odoo?.__WOWL_DEBUG__?.root?.env?.services?.action)',
            returnByValue: true
        });
        if (check.result?.value) break;
    }

    console.log("1. Testing Gantt View with Kanban Header...");
    const actResult = await send('Runtime.evaluate', {
        expression: `(async () => {
            try {
                const actionService = odoo.__WOWL_DEBUG__.root.env.services.action;
                const res = await actionService.doAction(217);
                return { res };
            } catch (e) {
                return { error: e.message, stack: e.stack };
            }
        })()`,
        awaitPromise: true,
        returnByValue: true
    });
    console.log("doAction Gantt:", JSON.stringify(actResult.result?.value));
    await new Promise(r => setTimeout(r, 4000));

    const checkDom = await send('Runtime.evaluate', {
        expression: `(() => {
            const cur = odoo.__WOWL_DEBUG__.root.env.services.action.currentController;
            const cp = document.querySelector('.o_control_panel');
            return {
                actionName: cur?.action?.name,
                viewType: cur?.view?.type,
                hasControlPanel: Boolean(cp),
                cpText: cp?.innerText?.slice(0, 500),
                switchButtons: Array.from(document.querySelectorAll('.o_cp_switch_buttons button')).map(b => b.className + ' - ' + b.title)
            };
        })()`,
        returnByValue: true
    });
    console.log("Gantt view status:", JSON.stringify(checkDom.result?.value, null, 2));

    const ssGantt = await send('Page.captureScreenshot');
    fs.writeFileSync('C:/Odoo/odoo/custom/school_management/scratch/verify_gantt_header.png', Buffer.from(ssGantt.data, 'base64'));

    console.log("2. Testing List View...");
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
            const ths = Array.from(document.querySelectorAll('.o_list_table th')).map(th => th.innerText.trim()).filter(Boolean);
            const rowCount = document.querySelectorAll('.o_list_table tbody tr').length;
            const headerBtns = Array.from(document.querySelectorAll('.o_list_selection_box button, .o_control_panel_main_buttons button')).map(b => b.innerText.trim()).filter(Boolean);
            return { ths, rowCount, headerBtns };
        })()`,
        returnByValue: true
    });
    console.log("List View info:", JSON.stringify(listInfo.result?.value, null, 2));

    const ssList = await send('Page.captureScreenshot');
    fs.writeFileSync('C:/Odoo/odoo/custom/school_management/scratch/verify_improved_list.png', Buffer.from(ssList.data, 'base64'));

    console.log("3. Testing Kanban View...");
    await send('Runtime.evaluate', {
        expression: `(async () => {
            const actionService = odoo.__WOWL_DEBUG__.root.env.services.action;
            return await actionService.doAction(217, { viewType: 'kanban' });
        })()`,
        awaitPromise: true,
        returnByValue: true
    });
    await new Promise(r => setTimeout(r, 3000));

    const kanbanInfo = await send('Runtime.evaluate', {
        expression: `(() => {
            return {
                cardCount: document.querySelectorAll('.o_kanban_record').length,
                groupCount: document.querySelectorAll('.o_kanban_group').length
            };
        })()`,
        returnByValue: true
    });
    console.log("Kanban View info:", JSON.stringify(kanbanInfo.result?.value, null, 2));

    const ssKanban = await send('Page.captureScreenshot');
    fs.writeFileSync('C:/Odoo/odoo/custom/school_management/scratch/verify_kanban_view.png', Buffer.from(ssKanban.data, 'base64'));

    ws.close();
    chromeProc.kill();
    console.log("Verification completed successfully!");
}
verify().catch(console.error);
