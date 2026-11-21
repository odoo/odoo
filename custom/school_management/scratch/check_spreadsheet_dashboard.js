const { spawn } = require('child_process');
const fs = require('fs');

async function test() {
    console.log("Authenticating admin session...");
    const authResp = await fetch('http://localhost:8070/web/session/authenticate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ jsonrpc: '2.0', params: { db: 'odoo', login: 'admin', password: 'admin' } })
    });
    const authData = await authResp.json();
    console.log("Logged in user:", authData.result?.name || "OK");

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
    console.log("Session ID obtained:", sessionId ? sessionId.slice(0, 10) + "..." : "none");

    const chromeProc = spawn('C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe', [
        '--headless=new', '--remote-debugging-port=9235', '--disable-gpu', '--window-size=1920,1080', 'about:blank'
    ]);
    await new Promise(r => setTimeout(r, 2000));
    const targetsRes = await fetch('http://localhost:9235/json');
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
    
    console.log("Navigating to Spreadsheet Dashboards...");
    await send('Page.navigate', { url: 'http://localhost:8070/odoo/dashboards' });
    await new Promise(r => setTimeout(r, 8000));

    // Inspect dashboard groups and items in the UI
    const dashInfo = await send('Runtime.evaluate', {
        expression: `(() => {
            const bodyText = document.body.innerText;
            const hasEduGroup = bodyText.includes('Education & Academic Management') || bodyText.includes('Education');
            const hasEduDash = bodyText.includes('Academic & Student Analytics') || bodyText.includes('Academic');
            
            // Find and click Education or Academic dashboard item
            const allElements = Array.from(document.querySelectorAll('*'));
            const eduItem = allElements.find(e => 
                e.children.length === 0 && (e.innerText?.trim() === 'Academic & Student Analytics' || e.innerText?.trim() === 'Education & Academic Management')
            );
            if (eduItem) {
                eduItem.click();
            }

            return {
                hasEduGroup,
                hasEduDash,
                clickedItem: eduItem ? eduItem.innerText.trim() : null,
                bodySnippet: bodyText.slice(0, 500)
            };
        })()`,
        returnByValue: true
    });
    console.log("Spreadsheet Dashboards Info:\n", JSON.stringify(dashInfo.result?.value, null, 2));

    await new Promise(r => setTimeout(r, 4000));
    const canvasCheck = await send('Runtime.evaluate', {
        expression: `(() => {
            const canvas = document.querySelector('canvas');
            const spContainer = document.querySelector('.o-spreadsheet') || document.querySelector('.o_spreadsheet_dashboard_action');
            const text = document.body.innerText;
            return {
                hasCanvas: Boolean(canvas),
                hasSpContainer: Boolean(spContainer),
                containsHarvard: text.includes('HARVARD') || text.includes('Academic & Student Analytics'),
                textSnippet: text.slice(0, 400)
            };
        })()`,
        returnByValue: true
    });
    console.log("Canvas / Spreadsheet render check:\n", JSON.stringify(canvasCheck.result?.value, null, 2));

    const ss = await send('Page.captureScreenshot');
    fs.writeFileSync('C:/Odoo/odoo/custom/school_management/scratch/spreadsheet_academic_dashboard_verified.png', Buffer.from(ss.data, 'base64'));
    console.log('Saved screenshot to custom/school_management/scratch/spreadsheet_academic_dashboard_verified.png');

    ws.close();
    chromeProc.kill();
}
test().catch(console.error);
