/** @odoo-module */

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('access_helpdesk_article_portal_tour', {
    test: true,
    steps: () => [{
    content: "clik on 'Help'",
    trigger: 'a[role="menuitem"]:contains("Help")',
}, {
    content: "Write 'Article' in the search bar",
    trigger: 'input[name="search"]',
    run: 'text Article'
}, {
    content: "Check that results contain 'Helpdesk Article'",
    trigger: '.dropdown-item:contains("Helpdesk Article")',
    run() {},
}, {
    content: "Check that results contain 'Child Article'",
    trigger: '.dropdown-item:contains("Child Article")',
    run() {},
}, {
    content: "Check that results don't contain 'Other Article'",
    trigger: '.dropdown-menu:not(:has(.dropdown-item:contains("Other Article")))',
    run() {},
}]});
