odoo.define('sale_crm.tour', function(require) {
"use strict";


var core = require('web.core');
var tour = require('web_tour.tour');
var sale_tour = require('sale.tour');

var _t = core._t;

tour.tours.sale_tour.steps.splice(1, 1,
{
    trigger: ".o_kanban_manage_button_section",
    content: _t("Click here to see more options."),
    position: "bottom"
}, {
    trigger: '.o_kanban_manage_view div:nth(2)',
    content: _t("Let\'s have a look at the quotations of this sales team."),
    position: "right"
});

});