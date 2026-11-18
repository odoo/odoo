/** @odoo-module */

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("website_sale_autocomplete_places_api_switch", {
    url: "/odoo/action-website.action_website_configuration",
    steps: () => [
        {
            content: "Switch to the Places API (New)",
            trigger: "#autocomplete_googleplaces_setting .alert-warning button[name='action_google_places_switch_to_api_new']",
            run: "click",
        },
        {
            content: "The deprecation warning is gone once the settings are reloaded",
            trigger: "#autocomplete_googleplaces_setting:not(:has(.alert-warning))",
        },
    ],
});
