import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("google_address_autocomplete_places_api_switch", {
    url: "/odoo/action-base_setup.action_general_configuration",
    steps: () => [
        {
            content: "Switch to the Places API (New)",
            trigger: "#google_address_autocomplete .alert-warning button[name='action_google_places_switch_to_api_new']",
            run: "click",
        },
        {
            content: "The deprecation warning is gone once the settings are reloaded",
            trigger: "#google_address_autocomplete:not(:has(.alert-warning))",
        },
    ],
});
