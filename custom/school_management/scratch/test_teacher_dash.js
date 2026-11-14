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
        '--headless=new', '--remote-debugging-port=9229', '--disable-gpu', '--window-size=1920,1080', 'about:blank'
    ]);
    await new Promise(r => setTimeout(r, 2000));
    const targetsRes = await fetch('http://localhost:9229/json');
    const targets = await targetsRes.json();
    const pageTarget = targets.find(t => t.type === 'page');
    const ws = new WebSocket(pageTarget.webSocketDebuggerUrl);
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
    await send('Page.navigate', { url: 'http://localhost:8070/odoo?action=teacher_dashboard_shell' });

    console.log("Waiting for dashboard to finish loading...");
    let loaded = false;
    for (let i = 0; i < 30; i++) {
        await new Promise(r => setTimeout(r, 1000));
        const check = await send('Runtime.evaluate', {
            expression: 'Boolean(document.querySelector(".o_teacher_hub_card"))',
            returnByValue: true
        });
        if (check.result?.value) {
            loaded = true;
            console.log(`Dashboard hub loaded after ${i + 1}s!`);
            break;
        }
    }

    if (!loaded) {
        console.log("Dashboard did not load in time!");
        const bodySnippet = await send('Runtime.evaluate', {
            expression: 'document.body.innerText.slice(0, 500)',
            returnByValue: true
        });
        console.log("Body snippet:", bodySnippet.result?.value);
        ws.close();
        chromeProc.kill();
        return;
    }

    // Click Exams & Marksheets tab
    const clickExamTab = await send('Runtime.evaluate', {
        expression: `(() => {
            const btns = Array.from(document.querySelectorAll('.o_teacher_hub_card button, .o_teacher_hub_card a'));
            const b = btns.find(x => x.innerText.includes('Exams & Marksheets') || x.innerText.includes('Exams'));
            if (b) { b.click(); return 'CLICKED: ' + b.innerText.replace(/\\s+/g, ' '); }
            return 'EXAMS BUTTON NOT FOUND among ' + btns.map(x => x.innerText.replace(/\\s+/g, ' ')).join(' | ');
        })()`,
        returnByValue: true
    });
    console.log('Click result:', clickExamTab.result?.value);
    await new Promise(r => setTimeout(r, 2000));

    const examInfo = await send('Runtime.evaluate', {
        expression: `(() => {
            const kpis = Array.from(document.querySelectorAll('.o_exam_kpi_card')).map(x => x.innerText.replace(/\\s+/g, ' ').trim());
            const rows = Array.from(document.querySelectorAll('table tbody tr')).map(tr => {
                const cols = Array.from(tr.querySelectorAll('td')).map(td => td.innerText.replace(/\\s+/g, ' ').trim());
                return cols.slice(0, 5);
            });
            const sideMarksheet = Array.from(document.querySelectorAll('.o_sidebar_card')).find(c => c.innerText.includes('Quick Marksheets'));
            return {
                kpiCards: kpis,
                totalTableRows: rows.length,
                firstThreeExams: rows.slice(0, 3),
                sidebarWidget: sideMarksheet ? sideMarksheet.innerText.replace(/\\s+/g, ' ').slice(0, 300) : null
            };
        })()`,
        returnByValue: true
    });
    console.log('Exams & Marksheets Hub Details:\n', JSON.stringify(examInfo.result?.value, null, 2));

    const ss = await send('Page.captureScreenshot');
    fs.writeFileSync('C:/Odoo/odoo/custom/school_management/scratch/teacher_dash_exams_tab.png', Buffer.from(ss.data, 'base64'));
    console.log('Saved exams tab screenshot to C:/Odoo/odoo/custom/school_management/scratch/teacher_dash_exams_tab.png');

    ws.close();
    chromeProc.kill();
}
test().catch(console.error);
