/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_manufacture_from_bom", {
    test: true,
    steps: () => [
        {
            trigger: '[name="product_tmpl_id"]',
        },
        {
            trigger: '.o_stat_text:contains("BoM Overview")',
        },
        {
            trigger: 'button.btn-primary:contains("Manufacture")',
        },
        {
            trigger: 'button[aria-checked="true"]:contains("Draft")',
            isCheck: true,
        },
    ],
});
