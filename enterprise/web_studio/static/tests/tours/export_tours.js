import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("can_export_new_module", {
    url: "/odoo",
    steps: () => [
        {
            trigger: ".o_home_menu_background .o_home_menu",
        },
        {
            trigger: ".o_web_studio_navbar_item > .o_nav_entry",
            run: "click",
        },
        {
            trigger: ".o_app.o_web_studio_new_app",
            run: "click",
        },
        {
            trigger: ".o_web_studio_app_creator_next",
            run: "click",
        },
        {
            trigger: ".o_input[name='appName']",
            run: "edit My New App",
        },
        {
            trigger: ".o_web_studio_app_creator_next",
            run: "click",
        },
        {
            trigger: ".o_input[name='menuName']",
            run: "edit My App Records",
        },
        {
            trigger: ".o_web_studio_app_creator_next",
            run: "click",
        },
        {
            trigger: ".o_web_studio_model_configurator_next",
            run: "click",
        },
        {
            trigger: ".o_form_renderer div:contains(description)",
        },
        {
            trigger: ".o_web_studio_leave > a",
            run: "click",
        },
        {
            trigger: ".o_form_renderer h1 input[placeholder^='Name']",
        },
        {
            trigger: ".o_menu_toggle:contains(my new app)",
            run: "click",
        },
        {
            trigger: ".o_web_studio_navbar_item > .o_nav_entry",
            run: "click",
        },
        {
            trigger: ".o_web_studio_export",
            run: "click",
        },
        {
            content: "check that export feature is blazing fast",
            trigger: ".modal .modal-footer button:contains(export)",
            run: "click",
        },
        {
            content: "close modal",
            trigger: ".modal .modal-footer button:contains(cancel)",
            run: "click",
        },
    ],
});
