const fs = require('fs');
const { spawn } = require('child_process');

async function run() {
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
    console.log("Session ID obtained:", sessionId ? sessionId.slice(0, 10) + "..." : "none");

    const chromeProc = spawn('C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe', [
        '--headless=new', '--remote-debugging-port=9232', '--disable-gpu', '--window-size=1920,1080', 'about:blank'
    ]);
    await new Promise(r => setTimeout(r, 2000));

    const targetsRes = await fetch('http://localhost:9232/json');
    const targets = await targetsRes.json();
    const pageTarget = targets.find(t => t.type === 'page');
    const ws = new WebSocket(pageTarget.webSocketDebuggerUrl);
    await new Promise(r => { ws.onopen = r; });

    let id = 1;
    function send(method, params = {}) {
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
    
    console.log("Navigating to Teacher Dashboard...");
    await send('Page.navigate', { url: 'http://localhost:8070/odoo?action=teacher_dashboard_shell' });
    await new Promise(r => setTimeout(r, 6000));

    // Check dashboard presence
    const dashCheck = await send('Runtime.evaluate', {
        expression: 'Boolean(document.querySelector(".o_teacher_dashboard"))',
        returnByValue: true
    });
    console.log("Dashboard container present:", dashCheck.result?.value);

    // Click Exams & Marksheets Tab
    const clickTab = await send('Runtime.evaluate', {
        expression: `(() => {
            const btns = Array.from(document.querySelectorAll('button'));
            const tabBtn = btns.find(b => b.innerText.includes('Exams & Marksheets') || b.innerText.includes('Exams'));
            if (tabBtn) {
                tabBtn.click();
                return 'Tab Clicked: ' + tabBtn.innerText.replace(/\\s+/g, ' ').trim();
            }
            return 'Tab button not found';
        })()`,
        returnByValue: true
    });
    console.log(clickTab.result?.value);
    await new Promise(r => setTimeout(r, 2000));

    // Extract exams metrics and table row details
    const domData = await send('Runtime.evaluate', {
        expression: `(() => {
            const kpis = Array.from(document.querySelectorAll('.o_exam_kpi_card')).map(c => c.innerText.replace(/\\s+/g, ' ').trim());
            const rows = Array.from(document.querySelectorAll('table tbody tr')).map(tr => {
                const tds = Array.from(tr.querySelectorAll('td')).map(td => td.innerText.replace(/\\s+/g, ' ').trim());
                return tds.slice(0, 4);
            });
            const sidebarExams = Array.from(document.querySelectorAll('.o_sidebar_card')).find(c => c.innerText.includes('Quick Marksheets'));
            return {
                kpiCount: kpis.length,
                kpis: kpis,
                rowCount: rows.length,
                sampleRows: rows.slice(0, 3),
                hasSidebarWidget: Boolean(sidebarExams),
                sidebarSnippet: sidebarExams ? sidebarExams.innerText.slice(0, 150) : null
            };
        })()`,
        returnByValue: true
    });
    console.log("Dashboard Exams Data:", JSON.stringify(domData.result?.value, null, 2));

    // Capture screenshot
    const ss = await send('Page.captureScreenshot');
    fs.writeFileSync('custom/school_management/scratch/teacher_dashboard_exams_live.png', Buffer.from(ss.data, 'base64'));
    console.log("Screenshot successfully saved to scratch/teacher_dashboard_exams_live.png");

    ws.close();
    chromeProc.kill();
}

run().catch(console.error);
