import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("website_settings_preselect_tour", {
    url: "/odoo",
    steps: () => [
        {
            content: "Click on Configuration menu",
            trigger:
                'button.dropdown-toggle[data-menu-xmlid="website.menu_website_global_configuration"]',
            run: "click",
        },
        {
            content: "Click on Settings",
            trigger: 'a.dropdown-item[data-menu-xmlid="website.menu_website_website_settings"]',
            run: "click",
        },
        {
            content: "Wait for the settings form view to load",
            trigger: ".o_settings_container",
        },
        {
            content: "Verify that website_id field has preselected Website 2",
            trigger: '.app_settings_header div[name="website_id"] .o-autocomplete--input',
            run: () => {
                const input = document.querySelector(
                    '.app_settings_header div[name="website_id"] .o-autocomplete--input'
                );
                if (!input || input.value !== "Website 2") {
                    throw new Error(
                        `Expected website_id input value to be 'Website 2', but got '${input?.value}'`
                    );
                }
            },
        },
    ],
});
