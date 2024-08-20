/** @odoo-module **/

import { registerOption } from "@web_editor/js/editor/snippets.registry";


export function registerWebsiteOption(name, def, options) {
    if (!def.module) {
        def.module = "website";
    }
    return registerOption(name, def, options);
}

registerWebsiteOption("WebsiteIconTools", {
    template: "web_editor.IconTools",
    selector: "span.fa, i.fa",
    exclude: "[data-oe-xpath]",
});

registerWebsiteOption("BadgeOptions", {
    template: "website.s_badge_options",
    selector: ".s_badge",
});

registerWebsiteOption("WebsiteHrOptions", {
    template: "website.s_hr_options",
    selector: ".s_hr",
    target: "hr",
});
