odoo.define("website.tour.restricted_editor", function (require) {
"use strict";

var tour = require("web_tour.tour");

tour.register("restricted_editor", {
    test: true,
    url: "/",
}, [{
    trigger: 'a.o_frontend_to_backend_edit_btn',
    content: "Click \"EDIT\" button of website as Restricted Editor",
    extra_trigger: ".homepage",
}, {
    trigger: '#oe_snippets.o_loaded',
    content: "Check that the snippets loaded properly",
}]);
});
