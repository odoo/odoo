/** @odoo-module */
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("web_enterprise.test_studio_list_upsell", {
    steps: () => [
        {
            trigger: ".o_list_view",
        },
        {
            trigger: ".o_optional_columns_dropdown > button",
            run: "click",
        },
        {
            trigger: " .o-dropdown--menu .dropdown-item-studio",
        },
    ],
});
