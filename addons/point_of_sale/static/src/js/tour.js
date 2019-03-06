odoo.define('point_of_sale.tour', function(require) {
"use strict";

var core = require('web.core');
var tour = require('web_tour.tour');

var _t = core._t;

tour.register('point_of_sale_tour', {
    url: "/web",
    rainbowMan: false,
}, [tour.STEPS.SHOW_APPS_MENU_ITEM, {
    trigger: '.o_app[data-menu-xmlid="point_of_sale.menu_point_root"]',
    content: _t("Ready to launch your <b>point of sale</b>? <i>Click here</i>."),
    position: 'right',
    edition: 'community'
}, {
    trigger: '.o_app[data-menu-xmlid="point_of_sale.menu_point_root"]',
    content: _t("Ready to launch your <b>point of sale</b>? <i>Click here</i>."),
    position: 'bottom',
    edition: 'enterprise'
}, {
    trigger: ".o_pos_kanban button.oe_kanban_action_button",
    content: _t("<p>Click to start the point of sale interface. It <b>runs on tablets</b>, laptops, or industrial hardware.</p><p>Once the session launched, the system continues to run without an internet connection.</p>"),
    position: "bottom"
}]);

});
