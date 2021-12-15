odoo.define("website.tour.snippet_countdown", function (require) {
"use strict";

const tour = require('web_tour.tour');
const wTourUtils = require('website.tour_utils');

tour.register('snippet_countdown', {
    test: true,
    url: '/?enable_editor=1',
}, [
    wTourUtils.dragNDrop({id: 's_countdown', name: 'Countdown'}),
    wTourUtils.clickOnSnippet({id: 's_countdown', name: 'Countdown'}),
    wTourUtils.changeOption('countdown', 'we-select:has([data-end-action]) we-toggler', 'end action'),
    wTourUtils.changeOption('countdown', 'we-button[data-end-action="message"]', 'end action'),
    wTourUtils.changeOption('countdown', 'we-button.toggle-edit-message', 'message preview'),
    // The next two steps check that the end message does not disappear when a
    // widgets_start_request is triggered.
    {
        content: "Hover the 'hide countdown at the end' button",
        trigger: '[data-select-class="hide-countdown"]',
        run: function (actions) {
            this.$anchor.trigger('mouseover');
            this.$anchor.trigger('mouseenter');
        },
    },
    {
        content: "Check that the countdown message is still displayed",
        trigger: '.s_countdown .s_picture',
        run: () => {
            // Just a visibility check

            // Also make sure the mouseout and mouseleave are triggered so that
            // next steps make sense.
            // TODO the next steps are not actually testing anything without
            // it and the mouseout and mouseleave make sense but really it
            // should not be *necessary* to simulate those for the editor flow
            // to make some sense.
            const $previousAnchor = $('[data-select-class="hide-countdown"]');
            $previousAnchor.trigger('mouseout');
            $previousAnchor.trigger('mouseleave');
        },
    },
    // Next, we change the end action to redirect while the edit message toggle
    // is still activated. Now, we can check if the countdown cannot be hidden
    // by mistake.
    wTourUtils.changeOption('countdown', 'we-select:has([data-end-action]) we-toggler', 'end action'),
    wTourUtils.changeOption('countdown', 'we-button[data-end-action="redirect"]', 'end action'),
    {
        content: "Click on the 'hide countdown at the end' button",
        trigger: '[data-select-class="hide-countdown"] we-checkbox',
        run: function (actions) {
            actions.auto();

            // Needed since the bug this test is covering occured after a small
            // delay.
            // TODO should really be more robust
            setTimeout(() => {
                document.body.classList.add('o_countdown_tour_small_delay');
            }, 100);
        },
    },
    {
        content: "Check that the countdown is still displayed",
        trigger: '.s_countdown_canvas_wrapper',
        extra_trigger: '.o_countdown_tour_small_delay',
        run: () => null, // Just a visibility check
    },
]);
});
