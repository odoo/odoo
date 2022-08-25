odoo.define('crm_iap_mine.generate_leads_steps', function (require) {
"use strict";

var tour = require('web_tour.tour');
const {Markup} = require('web.utils');
var core = require('web.core');

require('@crm/js/tours/crm');
var _t = core._t;

var DragOppToWonStepIndex = _.findIndex(tour.tours.crm_tour.steps, function (step) {
    return (step.id === 'drag_opportunity_to_won_step');
});

tour.tours.crm_tour.steps.splice(DragOppToWonStepIndex + 1, 0, {
    /**
     * Add some steps between "Drag your opportunity to <b>Won</b> when you get
     * the deal. Congrats !" and "Let’s have a look at an Opportunity." to
     * include the steps related to the lead generation (crm_iap_mine).
     * This eases the on boarding for the Lead Generation process.
     *
     */
    trigger: ".o_button_generate_leads",
    content: Markup(_t("Looking for more opportunities ?<br>Try the <b>Lead Generation</b> tool.")),
    position: "bottom",
    run: function (actions) {
        actions.auto('.o_button_generate_leads');
    },
}, {
    trigger: '.modal-body .o_industry',
    content: _t("Which Industry do you want to target?"),
    position: "right",
}, {
    trigger: '.modal-footer button[name=action_submit]',
    content: _t("Now, just let the magic happen!"),
    position: "bottom",
    run: function (actions) {
        actions.auto('.modal-footer button[special=cancel]');
}
});

});
