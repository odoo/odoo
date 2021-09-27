/** @odoo-module */
import { registry } from "@web/core/registry";
import { DebugMenu } from "@web/core/debug/debug_menu";
import { createDebugContext } from "@web/core/debug/debug_context";

const debugMenuService = {
    dependencies: ["command", "localization", "orm"],
    start(env) {
        if (env.debug) {
            const systray = document.querySelector('.o_menu_systray');
            if (systray) {
                Object.assign(env, createDebugContext(env, {categories: ["default"]}));
                owl.mount(DebugMenu, {
                    target: systray,
                    position: 'first-child',
                    env,
                });
            }
        }
    }
};
registry.category("services").add("website_debug_menu", debugMenuService);
