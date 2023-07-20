/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('portal_load_homepage', {
    test: true,
    url: '/my',
    steps: () => [
        {
            content: "Check portal is loaded",
            trigger: 'a[href*="/my/account"]:contains("Edit"):first',
        },
        {
            content: "Load my account details",
            trigger: 'input[value="Joel Willis"]',
            isCheck: true,
        }
    ]
});
