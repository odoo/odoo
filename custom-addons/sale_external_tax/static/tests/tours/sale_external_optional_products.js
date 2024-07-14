/** @odoo-module **/

import { registry } from "@web/core/registry";

// This tour relies on data created on the Python test.
registry.category("web_tour.tours").add('sale_external_optional_products', {
    test: true,
    url: '/my/quotes',
    steps: () => [
    {
        content: "open the test SO",
        trigger: 'a:containsExact("test")',
    },
    {
        content: "add the optional product",
        trigger: '.js_add_optional_products',
    },
    {
        content: "increase the quantity of the optional product by 1",
        extra_trigger: 'li a:contains("Communication history")', // Element on the left
        trigger: '.js_update_line_json:nth(1)',
    },
    {
        content: "wait for the quantity to be updated",
        trigger: 'input.js_quantity:propValue(2.0)',
        extra_trigger: 'li a:contains("Communication history")',
        run() {},
    },
    {
        content: "delete the optional line",
        trigger: '.js_update_line_json:nth(2)',
    },
    {
        content: "wait for line to be deleted and show up again in optional products",
        trigger: '.js_add_optional_products',
        run() {}, // it should not click
    },
]});
