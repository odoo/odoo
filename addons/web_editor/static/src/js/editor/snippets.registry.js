/** @odoo-module **/
import { registry } from "@web/core/registry";


export function registerOption(name, def, options) {
    if (!def.module) {
        def.module = "web_editor";
    }
    return registry.category("snippet_options").add(name, def, options);
}
