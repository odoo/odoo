/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('test_reordering_rule_with_variant_product', {
    steps: () => [
    {
        trigger: 'span:contains("KRIP T-Shirt")',
        run: "click",
    },
    {
        trigger: '.o_button_more',
        run: "click",
    },
    {
        trigger: "button[name='action_view_orderpoints']",
        run: "click",
    },
    {
        trigger: '.o_list_button_add',
        run: "click",
    }
]});
