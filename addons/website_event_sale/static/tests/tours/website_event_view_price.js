/** @odoo-module */

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('view_ticket_price', {
    test: true,
    steps: () => [{
        content: "Open the register modal",
        trigger: 'button[data-bs-target="#modal_ticket_registration"]',
    }, {
        content: "Select price of FR ticket",
        trigger: '.o_wevent_ticket_selector:contains($):contains(33.33)',
        isCheck: true,
    }]
});
