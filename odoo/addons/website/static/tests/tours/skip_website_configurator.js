/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('skip_website_configurator', {
    test: true,
    url: '/web#action=website.action_website_configuration',
    steps: () => [
    {
        content: "create a new website",
        trigger: 'button[name="action_website_create_new"]',
    },
    {
        content: "insert website name",
        trigger: 'div[name="name"] input',
        run: 'text Website EN'
    },
    {
        content: "validate the website creation modal",
        trigger: 'button.btn-primary'
    },
    {
        content: "skip configurator",
        // This trigger targets the skip button, it doesn't have a more
        // explicit class or ID.
        trigger: '.o_configurator_container .container-fluid .btn.btn-link'
    },
    {
        content: "make hover button appear",
        trigger: '.o_theme_preview',
        run: () => {
            $('.o_theme_preview .o_button_area').attr('style', 'visibility: visible; opacity: 1;');
        },
    },
    {
        content: "Install a theme",
        trigger: 'button[name="button_choose_theme"]'
    },
    {
        content: "Check that the homepage is loaded",
        trigger: ".o_website_preview[data-view-xmlid='website.homepage']",
        extra_trigger: ".o_menu_systray .o_user_menu",
        timeout: 30000,
        isCheck: true,
    },
]});
