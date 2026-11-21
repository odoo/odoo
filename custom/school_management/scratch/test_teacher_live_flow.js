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
        '--headless=new', '--remote-debugging-port=9240', '--disable-gpu', '--window-size=1920,1080', 'about:blank'
    ]);
    await new Promise(r => setTimeout(r, 2000));
    const targetsRes = await fetch('http://localhost:9240/json');
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
    
    console.log("Navigating to Harvard University Dashboard as Teacher...");
    await send('Page.navigate', { url: 'http://localhost:8070/odoo' });
    await new Promise(r => setTimeout(r, 7000));

    // 1. Inspect initial teacher dashboard UI
    const initCheck = await send('Runtime.evaluate', {
        expression: `(() => {
            const hasTeacherDash = Boolean(document.querySelector('.o_teacher_dashboard'));
            const tabs = Array.from(document.querySelectorAll('.nav-link, button')).map(b => b.innerText.trim()).filter(Boolean);
            const bodySnippet = document.body.innerText.slice(0, 400);
            return {
                hasTeacherDash,
                tabs: tabs.slice(0, 15),
                bodySnippet
            };
        })()`,
        returnByValue: true
    });
    console.log("Initial Dashboard Check:\n", JSON.stringify(initCheck.result?.value, null, 2));

    const ss1 = await send('Page.captureScreenshot');
    fs.writeFileSync('custom/school_management/scratch/teacher_dash_verified_step1.png', Buffer.from(ss1.data, 'base64'));

    // 2. Click on Exams & Marksheets tab
    const tabClick = await send('Runtime.evaluate', {
        expression: `(() => {
            const btns = Array.from(document.querySelectorAll('button'));
            const examBtn = btns.find(b => b.innerText.includes('Exams & Marksheets') || b.innerText.includes('Exams'));
            if (examBtn) {
                examBtn.click();
                return { clicked: true, text: examBtn.innerText.trim() };
            }
            return { clicked: false };
        })()`,
        returnByValue: true
    });
    console.log("Exam Tab Click:\n", JSON.stringify(tabClick.result?.value, null, 2));
    await new Promise(r => setTimeout(r, 2000));

    const examsViewCheck = await send('Runtime.evaluate', {
        expression: `(() => {
            const text = document.body.innerText;
            const hasAnalyticsBtn = text.includes('Academic & Student Analytics');
            const hasExamHeader = text.includes('Course Examinations & Marksheets');
            const kpis = Array.from(document.querySelectorAll('.o_exam_kpi_card')).map(c => c.innerText.replace(/\\s+/g, ' ').trim());
            const rows = Array.from(document.querySelectorAll('table tbody tr')).map(tr => tr.innerText.replace(/\\s+/g, ' ').trim());
            return {
                hasAnalyticsBtn,
                hasExamHeader,
                kpiCount: kpis.length,
                rowCount: rows.length,
                sampleRow: rows[0] || null
            };
        })()`,
        returnByValue: true
    });
    console.log("Exams & Marksheets View:\n", JSON.stringify(examsViewCheck.result?.value, null, 2));

    const ss2 = await send('Page.captureScreenshot');
    fs.writeFileSync('custom/school_management/scratch/teacher_dash_verified_step2_exams.png', Buffer.from(ss2.data, 'base64'));

    // 3. Test clicking Academic & Student Analytics button
    const clickAnalytics = await send('Runtime.evaluate', {
        expression: `(() => {
            const btns = Array.from(document.querySelectorAll('button'));
            const aBtn = btns.find(b => b.innerText.includes('Academic & Student Analytics') || b.innerText.includes('Spreadsheet Analytics'));
            if (aBtn) {
                aBtn.click();
                return { clicked: true, text: aBtn.innerText.trim() };
            }
            return { clicked: false };
        })()`,
        returnByValue: true
    });
    console.log("Click Analytics Button:\n", JSON.stringify(clickAnalytics.result?.value, null, 2));
    await new Promise(r => setTimeout(r, 5000));

    const spreadsheetCheck = await send('Runtime.evaluate', {
        expression: `(() => {
            const hasCanvas = Boolean(document.querySelector('canvas'));
            const text = document.body.innerText;
            return {
                hasCanvas,
                containsEduGroup: text.includes('EDUCATION & ACADEMIC MANAGEMENT') || text.includes('Education'),
                containsAcademicDash: text.includes('Academic & Student Analytics'),
                textSnippet: text.slice(0, 300)
            };
        })()`,
        returnByValue: true
    });
    console.log("Spreadsheet Dash Check from Teacher:\n", JSON.stringify(spreadsheetCheck.result?.value, null, 2));

    const ss3 = await send('Page.captureScreenshot');
    fs.writeFileSync('custom/school_management/scratch/teacher_dash_verified_step3_spreadsheet.png', Buffer.from(ss3.data, 'base64'));

    ws.close();
    chromeProc.kill();
}
test().catch(console.error);
