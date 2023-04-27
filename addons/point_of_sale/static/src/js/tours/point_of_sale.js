odoo.define('point_of_sale.tour', function(require) {
"use strict";

var core = require('web.core');
var tour = require('web_tour.tour');

var _t = core._t;

tour.register('point_of_sale_tour', {
    url: "/web",
    rainbowMan: false,
    sequence: 45,
}, [tour.stepUtils.showAppsMenuItem(), {
    trigger: '.o_app[data-menu-xmlid="point_of_sale.menu_point_root"]',
    content: _t("Ready to launch your <b>point of sale</b>?"),
    width: 215,
    position: 'right',
    edition: 'community'
}, {
    trigger: '.o_app[data-menu-xmlid="point_of_sale.menu_point_root"]',
    content: _t("Ready to launch your <b>point of sale</b>?"),
    width: 215,
    position: 'bottom',
    edition: 'enterprise'
}, {
    trigger: ".o_pos_kanban button.oe_kanban_action_button",
    content: _t("<p>Ready to have a look at the <b>POS Interface</b>? Let's start our first session.</p>"),
    position: "bottom"
}]);

});
