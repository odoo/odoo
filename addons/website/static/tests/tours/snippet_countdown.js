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
        run: () => null, // Just a visibility check
    },
]);
});
