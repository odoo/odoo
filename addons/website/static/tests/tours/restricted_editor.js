odoo.define("website.tour.restricted_editor", function (require) {
"use strict";

var wTourUtils = require("website.tour_utils");

wTourUtils.registerWebsitePreviewTour("restricted_editor", {
    test: true,
    url: "/",
}, [{
    trigger: '.o_edit_website_container a',
    content: "Click \"EDIT\" button of website as Restricted Editor",
}, {
    trigger: '#oe_snippets.o_loaded',
    content: "Check that the snippets loaded properly",
}]);
});
