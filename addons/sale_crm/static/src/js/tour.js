odoo.define('sale_crm.tour', function(require) {
"use strict";

var core = require('web.core');
var tour = require('web_tour.tour');
require('sale.tour');

var _t = core._t;

var quotation_button_step_index = _.findIndex(tour.tours.sale_tour.steps, function (step) {
    return (step.id === "quotation_button_on_dashboard");
});

tour.tours.sale_tour.steps.splice(quotation_button_step_index, 1, {
    trigger: ".o_kanban_manage_button_section > a",
    content: _t("Click here to see more options."),
    position: "right"
}, {
    trigger: ".o_quotation_view_button",
    content: _t("Let's have a look at the quotations of this sales team."),
    position: "right"
});
});
