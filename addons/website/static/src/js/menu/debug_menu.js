/** @odoo-module */
import { registry } from "@web/core/registry";
import { DebugMenuBasic } from "@web/core/debug/debug_menu_basic";
import { createDebugContext } from "@web/core/debug/debug_context";

const { mount } = owl;
const debugMenuService = {
    dependencies: ["localization", "orm"],
    start(env) {
        if (env.debug) {
            const systray = document.querySelector('.o_menu_systray');
            if (systray) {
                Object.assign(env, createDebugContext(env, {categories: ["default"]}));
                mount(DebugMenuBasic, systray, {
                    position: 'first-child',
                    env,
                    templates: window.__ODOO_TEMPLATES__,
                });
            }
        }
    }
};
registry.category("services").add("website_debug_menu", debugMenuService);
