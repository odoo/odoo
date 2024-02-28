/** @odoo-module */

import wTourUtils from 'website.tour_utils';

wTourUtils.registerWebsitePreviewTour('snippet_countdown', {
    test: true,
    url: '/',
    edition: true,
}, [
    wTourUtils.dragNDrop({id: 's_countdown', name: 'Countdown'}),
    wTourUtils.clickOnSnippet({id: 's_countdown', name: 'Countdown'}),
    wTourUtils.changeOption('countdown', 'we-select:has([data-end-action]) we-toggler', 'end action'),
    wTourUtils.changeOption('countdown', 'we-button[data-end-action="message"]', 'end action'),
    wTourUtils.changeOption('countdown', 'we-button.toggle-edit-message', 'message preview'),
    // The next two steps check that the end message does not disappear when a
    // widgets_start_request is triggered.
    {
        content: "Hover an option which has a preview",
        trigger: '[data-select-class="o_half_screen_height"]',
        run: function (actions) {
            this.$anchor.trigger('mouseover');
            this.$anchor.trigger('mouseenter');
        },
    },
    {
        content: "Check that the countdown message is still displayed",
        trigger: 'iframe .s_countdown .s_picture',
        run: () => {
            // Just a visibility check

            // Also make sure the mouseout and mouseleave are triggered so that
            // next steps make sense.
            // TODO the next steps are not actually testing anything without
            // it and the mouseout and mouseleave make sense but really it
            // should not be *necessary* to simulate those for the editor flow
            // to make some sense.
            const $previousAnchor = $('[data-select-class="o_half_screen_height"]');
            $previousAnchor.trigger('mouseout');
            $previousAnchor.trigger('mouseleave');
        },
    },
    // Next, we change the end action to message and no countdown while the edit
    // message toggle is still activated. It should hide the countdown
    wTourUtils.changeOption('countdown', 'we-select:has([data-end-action]) we-toggler', 'end action'),
    wTourUtils.changeOption('countdown', 'we-button[data-end-action="message_no_countdown"]', 'end action'),
    {
        content: "Check that the countdown is not displayed",
        trigger: 'iframe .s_countdown:has(.s_countdown_canvas_wrapper:not(:visible))',
        run: () => null, // Just a visibility check
    },
    {
        content: "Check that the message is still displayed",
        trigger: 'iframe .s_countdown .s_picture',
        run: () => null, // Just a visibility check
    },
]);
