/** @odoo-module **/

import { registerOption } from "@web_editor/js/editor/snippets.registry";


export function registerWebsiteOption(name, def, options) {
    if (!def.module) {
        def.module = "website";
    }
    return registerOption(name, def, options);
}

