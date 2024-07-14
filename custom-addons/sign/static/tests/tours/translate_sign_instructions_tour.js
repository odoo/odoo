/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("translate_sign_instructions", {
    test: true,
    steps: () => [
        {
            content: "Translations must be loaded",
            trigger: 'iframe .o_sign_sign_item_navigator:contains("Cliquez pour commencer")',
            run: () => null, // it's a check
        },
    ],
});
