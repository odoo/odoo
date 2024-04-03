odoo.define('website_event_questions.tour_test_tickets_questions', function (require) {
'use strict';

var tour = require('web_tour.tour');
tour.register('test_tickets_questions', {
    test: true,
    url: '/event'
}, [{
    content: "Click on the Design Fair event",
    trigger: 'article:contains("Design Fair New York")',
}, {
    content: "Select 2 'Free' tickets to buy",
    trigger: 'div.row:contains("Free") select.form-select',
    run: 'text 2'
}, {
    content: "Click on Register tickets button",
    trigger: 'button:contains("Register")',
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
    trigger: 'div:contains("Ticket #1").modal-body select[name*="question_answer"]',
    run: 'text Vegetarian'
}, {
    trigger: 'div:contains("Ticket #1").modal-body textarea[name*="question_answer"]',
    run: 'text Fish and Nuts'
}, {
    trigger: 'div:contains("Ticket #2").modal-body input[name*="name"]',
    run: 'text Attendee B'
}, {
    trigger: 'div:contains("Ticket #2").modal-body input[name*="email"]',
    run: 'text attendee-b@gmail.com'
}, {
    trigger: 'div:contains("Ticket #2").modal-body select[name*="question_answer"]',
    run: 'text Pastafarian'
}, {
    trigger: 'div.o_wevent_registration_question_global select[name*="question_answer"]',
    run: 'text A friend'
}, {
    trigger: 'button:contains("Continue")',
    run: 'click'
}, {
    // The tour stops too early and the registration fails if we don't wait the confirmation.
    content: 'Wait for confirmation',
    trigger: '.o_wereg_confirmed, .oe_cart',
    auto: true
}]);

});
