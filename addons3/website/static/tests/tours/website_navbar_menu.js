/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("website_navbar_menu", {
    test: true,
    url: "/",
    steps: () => [
    {
        content: "Ensure menus are in DOM",
        trigger: '.top_menu .nav-item a:contains("Test Tour Menu")',
        run: function () {}, // it's a check
    }, {
        content: "Ensure menus loading is done (so they are actually visible)",
        trigger: 'body:not(:has(.o_menu_loading))',
        run: function () {}, // it's a check
    }
]});
