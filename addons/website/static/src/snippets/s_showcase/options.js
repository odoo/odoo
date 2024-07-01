/** @odoo-module **/

import {
    registerWebsiteOption,
} from "@website/js/editor/snippets.registry";

registerWebsiteOption("Showcase", {
    selector: ".s_showcase .row > div:has(> .s_showcase_title)",
});
