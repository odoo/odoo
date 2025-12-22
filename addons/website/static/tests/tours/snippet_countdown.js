/** @odoo-module */

import {
    changeOption,
    clickOnSnippet,
    insertSnippet,
    registerWebsitePreviewTour,
} from '@website/js/tours/tour_utils';

registerWebsitePreviewTour('snippet_countdown', {
    url: '/',
    edition: true,
}, () => [
    ...insertSnippet({id: "s_countdown", name: "Countdown", groupName: "Content"}),
    ...clickOnSnippet({id: 's_countdown', name: 'Countdown'}),
    changeOption('countdown', 'we-select:has([data-end-action]) we-toggler', 'end action'),
    changeOption('countdown', 'we-button[data-end-action="message"]', 'end action'),
    changeOption('countdown', 'we-button.toggle-edit-message', 'message preview'),
    // The next two steps check that the end message does not disappear when a
    // widgets_start_request is triggered.
    {
        content: "Hover an option which has a preview",
        trigger: '[data-select-class="o_half_screen_height"]',
        run: "hover",
    },
    {
        content: "Check that the countdown message is still displayed",
        trigger: ':iframe .s_countdown .s_picture',
        run() {
            // Just a visibility check

            // Also make sure the mouseout and mouseleave are triggered so that
            // next steps make sense.
            // TODO the next steps are not actually testing anything without
            // it and the mouseout and mouseleave make sense but really it
            // should not be *necessary* to simulate those for the editor flow
            // to make some sense.
            const previousAnchor = document.querySelector('[data-select-class="o_half_screen_height"]');
            previousAnchor.dispatchEvent(new Event("mouseout"));
            previousAnchor.dispatchEvent(new Event("mouseleave"));
        },
    },
    // Next, we change the end action to message and no countdown while the edit
    // message toggle is still activated. It should hide the countdown
    changeOption('countdown', 'we-select:has([data-end-action]) we-toggler', 'end action'),
    changeOption('countdown', 'we-button[data-end-action="message_no_countdown"]', 'end action'),
    {
        content: "Check that the countdown is not displayed",
        trigger: ':iframe .s_countdown:has(.s_countdown_canvas_wrapper:not(:visible))',
    },
    {
        content: "Check that the message is still displayed",
        trigger: ':iframe .s_countdown .s_picture',
    },
]);
