/** @odoo-module */

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('tests_shared_js_python', {
    test: true,
    url: "/account/init_tests_shared_js_python",
    steps: () => [
    {
        content: "Click",
        trigger: 'button',
    },
    {
        content: "Wait",
        trigger: 'button.text-success',
        timeout: 3000,
        run: () => {},
    },
]});
