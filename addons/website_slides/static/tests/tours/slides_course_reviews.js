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
}, {
    trigger: 'a[id="review-tab"]',
}, {
    shadow_dom: "#chatterRoot",
    trigger: ".o-mail-Chatter-content:not(:has(o-mail-Message-content))",
    run: function() {},
}, {
    shadow_dom: "#ratingComposerRoot",
    trigger: 'span:contains("Add Review")',
    // If it fails here, it means the log note is considered as a review
}, {
    shadow_dom: "#ratingComposerRoot",
    trigger: ".o-mail-Composer-input",
    run: "edit Great course!",
}, {
    shadow_dom: "#ratingComposerRoot",
    trigger: ".o-mail-Composer-send:enabled",
}, {
    trigger: 'a[id="review-tab"]',
    run: 'click',
}, {
    shadow_dom: "#ratingComposerRoot",
    trigger: 'span:contains("Edit Review")',
    // If it fails here, it means the system is allowing you to add another review.
}, {
    shadow_dom: "#ratingComposerRoot",
    trigger: '.o-mail-Composer-input',
    run: function() {
        if (this.anchor.value !== "Great course!") {
            throw new Error("Composer should contain previous message body.");
        }
    },
}
]});
