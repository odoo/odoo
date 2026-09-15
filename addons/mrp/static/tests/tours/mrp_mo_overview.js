/** @odoo-module **/
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("mrp_mo_overview_no_byproducts_tour", {
    steps: () => [
        {
            content: "Open the MO Overview",
            trigger: ".oe_stat_button:contains('Overview')",
            run: "click",
        },
        {
            content: "The overview must render the MO despite having no byproducts",
            trigger: "table[name='overview'] td:contains('MO Overview Test Product')",
        },
    ],
});
