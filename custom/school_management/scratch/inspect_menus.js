const fs = require('fs');

async function main() {
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
    const sessionData = await authResp.json();
    console.log('User uid:', sessionData.result?.uid);
    console.log('Cache hashes:', sessionData.result?.cache_hashes);
    const loadMenusHash = sessionData.result?.cache_hashes?.load_menus;
    console.log('loadMenusHash:', loadMenusHash);

    const menuUrl = `http://localhost:8070/web/webclient/load_menus/${loadMenusHash}`;
    const menusResp = await fetch(menuUrl, {
        headers: { 'Cookie': 'session_id=' + sessionId }
    });
    const menus = await menusResp.json();
    for (const [id, m] of Object.entries(menus)) {
        if (m.name && m.name.toLowerCase().includes('profile')) {
            console.log('Found profile menu:', id, m.name, m.xmlid, 'parent:', m.parent_id);
        }
    }
    const root = menus['root'];
    console.log('Root children:', root?.children?.map(c => menus[c]?.name));
    const schoolApp = Object.values(menus).find(m => m.xmlid === 'school_management.menu_school_root' || (m.name && m.name.includes('Harvard')));
    if (schoolApp) {
        console.log('School App children:', schoolApp.children?.map(c => menus[c]?.name));
    }
}
main().catch(console.error);
