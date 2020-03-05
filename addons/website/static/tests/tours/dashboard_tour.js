odoo.define("website.tour.backend_dashboard", function (require) {
"use strict";

var tour = require("web_tour.tour");

tour.register("backend_dashboard", {
    test: true,
    url: "/web",
}, [tour.stepUtils.showAppsMenuItem(),
    {
    trigger: 'a[data-menu-xmlid="website.menu_website_configuration"]',
}, {
    trigger: '.dropdown-toggle[data-menu-xmlid="website.menu_dashboard"]',
}, {
    trigger: '.dropdown-item[data-menu-xmlid="website.menu_website_google_analytics"]',
}, {
    // Visits section should always be present even when empty / not hooked to anything
    trigger: 'h2:contains("Visits")',
    content: "Check if dashboard loads",
    run: function () {}
}]);
});
