/** @odoo-module **/

import tour from 'web_tour.tour';

/**
 * This tour test that a log note isn't considered
 * as a course review. And also that a member can
 * add only one review.
 */
tour.register('course_reviews', {
    url: '/slides',
    test: true
}, [
{
    trigger: 'a:contains("Basics of Gardening - Test")',
}, {
    trigger: 'a[id="review-tab"]',
}, {
    trigger: '.o_portal_chatter_message:contains("Log note")',
    run: function() {},
}, {
    trigger: 'span:contains("Add Review")',
    // If it fails here, it means the log note is considered as a review
}, {
    trigger: 'div.o_portal_chatter_composer_body textarea',
    extra_trigger: 'div.modal_shown',
    run: 'text Great course!',
    in_modal: false,
}, {
    trigger: 'button.o_portal_chatter_composer_btn',
    in_modal: false,
}, {
    trigger: 'a[id="review-tab"]',
}, {
    trigger: 'button:contains("Visible")',
}, {
    trigger: 'span:contains("Edit Review")',
    // If it fails here, it means the system is allowing you to add another review.
}, {
    trigger: 'div.o_portal_chatter_composer_body textarea:contains("Great course!")',
    run: function() {},
}
]);
