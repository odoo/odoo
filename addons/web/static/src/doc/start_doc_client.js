import { App, whenReady } from "@odoo/owl";
import { DocClient } from "@web/doc/doc_client";

export const session = odoo.__session_info__ || {};

export async function startDocClient() {
    await whenReady();
    const app = new App(DocClient);
    app.mount(document.body);
}

if (session.isDoc) {
    startDocClient();
}
