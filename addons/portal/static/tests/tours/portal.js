/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('portal_load_homepage', {
    test: true,
    url: '/my',
    steps: () => [
        {
            content: "Check portal is loaded",
            trigger: 'a[role="button"]:contains("Edit"):first',
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
            content: "Address view is opened",
            trigger: 'a[href*="/my/home"]',
            run: "click",
        },
        {
            content: "Check that we are back on the portal",
            trigger: 'a[role="button"]:contains("Edit"):first',
        }
    ]
});

registry.category("web_tour.tours").add('portal_load_homepage_forbidden', {
    test: true,
    url: '/my',
    steps: () => [
        {
            content: "Check portal is loaded",
            trigger: 'a[role="button"]:contains("Edit"):first',
            run: "click",
        },
        {
            content: "Load my account details",
            trigger: 'h1:contains("403: Forbidden")',
        }
    ]
});
