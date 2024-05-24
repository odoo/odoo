/** @odoo-module **/

import { registry } from '@web/core/registry';

/**
 * This tour test that a log note isn't considered
 * as a course review. And also that a member can
 * add only one review.
 */
registry.category('web_tour.tours').add('course_reviews', {
    url: '/slides',
    test: true,
    steps: () => [
{
    trigger: 'a:contains("Basics of Gardening - Test")',
    run: "click",
}, {
    trigger: 'a[id="review-tab"]',
    run: "click",
}, {
    trigger: '.o_portal_chatter_message:contains("Log note")',
    run: function() {},
}, {
    trigger: 'span:contains("Add Review")',
    run: "click",
    // If it fails here, it means the log note is considered as a review
}, {
    trigger: 'div.o_portal_chatter_composer_body textarea',
    extra_trigger: 'div.modal_shown',
    in_modal: false,
    run: "edit Great course!",
}, {
    trigger: 'button.o_portal_chatter_composer_btn',
    in_modal: false,
    run: "click",
}, {
    trigger: 'a[id="review-tab"]',
    run: "click",
}, {
    trigger: 'label:contains("Public")',
    run: "click",
}, {
    trigger: 'span:contains("Edit Review")',
    run: "click",
    // If it fails here, it means the system is allowing you to add another review.
}, {
    trigger: "div.o_portal_chatter_composer_body textarea:value(Great course!)",
    run: function() {},
}
]});
