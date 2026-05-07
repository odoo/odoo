import { App, whenReady } from "@odoo/owl";
import { getTemplate } from "@web/core/templates";
import { HotkeyPlugin } from "@web/core/hotkeys/hotkey_plugin";
import { DocClient } from "@api_doc/doc_client";

export async function startDocClient(target) {
    await whenReady();
    target ??= document.body;
    const app = new App({ getTemplate, plugins: [HotkeyPlugin] });
    await app.pluginManager.ready;
    await app.createRoot(DocClient).mount(target);
    return app;
}
