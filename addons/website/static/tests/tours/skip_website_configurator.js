import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("skip_website_configurator", {
    url: "/odoo/action-website.action_website_configuration",
    steps: () => [
        {
            content: "create a new website",
            trigger: 'button[name="action_website_create_new"]',
            run: "click",
        },
        {
            content: "insert website name",
            trigger: 'div[name="name"] input',
            run: "edit Website EN",
        },
        {
            content: "validate the website creation modal",
            trigger: ".modal button.btn-primary",
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "skip configurator",
            // This trigger targets the skip button, it doesn't have a more
            // explicit class or ID.
            trigger: ".o_configurator_container .container-fluid .btn.btn-link",
            run: "click",
        },
        {
            content: "Check that the homepage is loaded",
            trigger: ".o_website_preview :iframe html[data-view-xmlid='website.homepage']",
            timeout: 30000,
        },
        {
            content: "Wait title is present before close tour",
            trigger: ":iframe h2:contains(welcome to your)",
        },
    ],
});
