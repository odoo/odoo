const { spawn } = require('child_process');
const fs = require('fs');

async function capture() {
    const chrome = spawn('C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe', [
        '--headless=new', '--remote-debugging-port=9255', '--disable-gpu', '--window-size=1600,1050', 'about:blank'
    ]);
    await new Promise(r => setTimeout(r, 2000));
    const targetsRes = await fetch('http://localhost:9255/json');
    const targets = await targetsRes.json();
    const ws = new WebSocket(targets.find(t => t.type === 'page').webSocketDebuggerUrl);
    await new Promise(r => { ws.onopen = r; });
    let id = 1;
    function send(m, p={}) {
        return new Promise(res => {
            const curId = id++;
            const h = (msg) => { const d = JSON.parse(msg.data); if (d.id === curId) { ws.removeEventListener('message', h); res(d.result); } };
            ws.addEventListener('message', h);
            ws.send(JSON.stringify({ id: curId, method: m, params: p }));
        });
    }
    await send('Page.enable');
    
    console.log("Navigating to HTML preview...");
    await send('Page.navigate', { url: 'file:///C:/Odoo/odoo/custom/school_management/scratch/exam_892_preview.html' });
    await new Promise(r => setTimeout(r, 2000));

    const checkText = await send('Runtime.evaluate', {
        expression: `(() => {
            const title = document.querySelector('div[style*=\"STUDENT EXAMINATION MARKSHEET\"]')?.innerText;
            const table = document.querySelector('table');
            const rows = document.querySelectorAll('tbody tr');
            return {
                bodyTextSnippet: document.body.innerText.slice(0, 500),
                rowCount: rows.length
            };
        })()`,
        returnByValue: true
    });
    console.log("Preview Check:", JSON.stringify(checkText.result?.value, null, 2));

    const ss = await send('Page.captureScreenshot');
    const outPng = 'C:/Odoo/odoo/custom/school_management/scratch/exam_marksheet_pdf_verified.png';
    fs.writeFileSync(outPng, Buffer.from(ss.data, 'base64'));
    console.log('Saved screenshot to:', outPng);

    const artPng = 'C:/Users/Rith2/.gemini/antigravity-acp/brain/78b4311f-52e2-48ba-b5c3-a1f375fd9f6c/exam_marksheet_pdf_verified.png';
    fs.copyFileSync(outPng, artPng);
    console.log('Copied screenshot to artifact directory:', artPng);

    ws.close();
    chrome.kill();
}
capture().catch(console.error);
