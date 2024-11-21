/** @odoo-module **/

import { registry } from "@web/core/registry";
registry.category("web_tour.tours").add('test_tickets_questions', {
    url: '/event',
    steps: () => [{
    content: "Click on the Design Fair event",
    trigger: 'article:contains("Design Fair New York")',
    run: "click",
}, {
    content: "Click on Register modal tickets button",
    trigger: 'button:contains("Register")',
    run: 'click'
}, {
    content: "Check Register button is disabled when no ticket selected",
    trigger: 'button:disabled:contains("Register")',
}, {
    content: "Select 2 'Free' tickets to buy",
    trigger: 'div.o_wevent_ticket_selector:contains("Free") select.form-select',
    run: "select 2",
}, {
    content: "Click on Register (to fill tickets data) button",
    trigger: 'div.modal-footer button:contains("Register")',
    run: 'click'
}, {
    trigger: 'div:contains("Ticket #1").modal-body input[name*="name"]',
    run: "edit Attendee A",
}, {
    trigger: 'div:contains("Ticket #1").modal-body input[name*="email"]',
    run: "edit attendee-a@gmail.com",
}, {
    trigger: 'div:contains("Ticket #1").modal-body input[name*="phone"]',
    run: "edit +32499123456",
}, {
    trigger: 'div:contains("Ticket #1").modal-body select[name*="1-simple_choice"]',
    run: "selectByLabel Vegetarian",
}, {
    trigger: 'div:contains("Ticket #1").modal-body textarea[name*="1-text_box"]',
    run: "edit Fish and Nuts",
}, {
    trigger: 'div:contains("Ticket #2").modal-body input[name*="name"]',
    run: "edit Attendee B",
}, {
    trigger: 'div:contains("Ticket #2").modal-body input[name*="email"]',
    run: "edit attendee-b@gmail.com",
}, {
    trigger: 'div:contains("Ticket #2").modal-body input[name*="company_name"]',
    run: "edit My Company",
}, {
    trigger: 'div:contains("Ticket #2").modal-body select[name*="2-simple_choice"]',
    run: "selectByLabel Pastafarian",
}, {
    trigger: 'div.o_wevent_registration_question_global select[name*="0-simple_choice"]',
    run: "selectByLabel A friend",
}, {
    trigger: ".modal#modal_attendees_registration:not(.o_inactive_modal) button[type=submit].btn-primary",
    run: 'click'
}, {
    // The tour stops too early and the registration fails if we don't wait the confirmation.
    content: 'Wait for confirmation',
    trigger: '.o_wereg_confirmed, .oe_cart',
}]});
