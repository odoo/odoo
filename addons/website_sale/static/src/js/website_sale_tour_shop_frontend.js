odoo.define("website_sale.tour_shop_frontend", function (require) {
"use strict";

var tour = require("web_tour.tour");
var base = require("web_editor.base");
var steps = require("website_sale.tour_shop");
tour.register("shop", {
    url: "/shop",
    wait_for: base.ready(),
}, steps);

});
