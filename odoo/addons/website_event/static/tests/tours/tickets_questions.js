/** @odoo-module **/

import { registry } from "@web/core/registry";
registry.category("web_tour.tours").add('test_tickets_questions', {
    test: true,
    url: '/event',
    steps: () => [{
    content: "Click on the Design Fair event",
    trigger: 'article:contains("Design Fair New York")',
}, {
    content: "Click on Register modal tickets button",
    trigger: 'button:contains("Register")',
    run: 'click'
}, {
    content: "Check Register button is disabled when no ticket selected",
    trigger: 'button:disabled:contains("Register")',
    isCheck: true,
}, {
    content: "Select 2 'Free' tickets to buy",
    trigger: 'div.o_wevent_ticket_selector:contains("Free") select.form-select',
    run: 'text 2'
}, {
    content: "Click on Register (to fill tickets data) button",
    trigger: 'div.modal-footer button:contains("Register")',
    run: 'click'
}, {
    trigger: 'div:contains("Ticket #1").modal-body input[name*="name"]',
    run: 'text Attendee A'
}, {
    trigger: 'div:contains("Ticket #1").modal-body input[name*="email"]',
    run: 'text attendee-a@gmail.com'
}, {
    trigger: 'div:contains("Ticket #1").modal-body input[name*="phone"]',
    run: 'text +32499123456'
}, {
    trigger: 'div:contains("Ticket #1").modal-body select[name*="1-simple_choice"]',
    run: 'text Vegetarian'
}, {
    trigger: 'div:contains("Ticket #1").modal-body textarea[name*="1-text_box"]',
    run: 'text Fish and Nuts'
}, {
    trigger: 'div:contains("Ticket #2").modal-body input[name*="name"]',
    run: 'text Attendee B'
}, {
    trigger: 'div:contains("Ticket #2").modal-body input[name*="email"]',
    run: 'text attendee-b@gmail.com'
}, {
    trigger: 'div:contains("Ticket #2").modal-body input[name*="company_name"]',
    run: 'text My Company'
}, {
    trigger: 'div:contains("Ticket #2").modal-body select[name*="2-simple_choice"]',
    run: 'text Pastafarian'
}, {
    trigger: 'div.o_wevent_registration_question_global select[name*="0-simple_choice"]',
    run: 'text A friend'
}, {
    trigger: 'button[type=submit]',
    run: 'click'
}, {
    // The tour stops too early and the registration fails if we don't wait the confirmation.
    content: 'Wait for confirmation',
    trigger: '.o_wereg_confirmed, .oe_cart',
    isCheck: true,
}]});
