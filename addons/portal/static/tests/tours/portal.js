/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('portal_load_homepage', {
    test: true,
    url: '/my',
    steps: () => [
        {
            content: "Check portal is loaded",
            trigger: 'a[href*="/my/account"]:contains("Edit"):first',
            run: "click",
        },
        {
            content: "Load my account details",
            trigger: 'input[value="Joel Willis"]',
            run: "click",
        },
        {
            content: 'type a different phone number',
            trigger: 'input[name="phone"]',
            run: "edit +1 555 666 7788",
        },
        {
            content: "Submit the form",
            trigger: 'button[type=submit]',
            run: "click",
        },
        {
            content: "Check that we are back on the portal",
            trigger: 'a[href*="/my/account"]:contains("Edit"):first',
        }
    ]
});
