odoo.define("website.tour.backend_dashboard", function (require) {
"use strict";

var tour = require("web_tour.tour");

tour.register("backend_dashboard", {
    test: true,
    url: "/web",
}, [tour.STEPS.SHOW_APPS_MENU_ITEM,
    {
    trigger: 'a[data-menu-xmlid="website.menu_website_configuration"]',
    run: 'click',
}, {
    trigger: '.dropdown-toggle[data-menu-xmlid="website.menu_dashboard"]',
    run: 'click',
}, {
    trigger: '.dropdown-item[data-menu-xmlid="website.menu_website_google_analytics"]',
    content: 'Check if traceback',
    run: 'click',
}]);
});
