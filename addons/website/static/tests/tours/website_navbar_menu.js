/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("website_navbar_menu", {
    url: "/",
    checkDelay: 50,
    steps: () => [
        {
            content: "Ensure menus are in DOM",
            trigger: ".top_menu .nav-item a:contains(Test Tour Menu)",
        },
        {
            content: "Ensure menus loading is done (so they are actually visible)",
            trigger: "body:not(:has(.o_menu_loading))",
        },
        {
            trigger: `.o_main_nav a[role="menuitem"]:contains(test tour menu)`,
            run: "click",
        },
        {
            trigger: `main:contains(We couldn't find the page you're looking for!)`,
        },
    ],
});
