/** @odoo-module */
import { registry } from "@web/core/registry"

registry.category("web_tour.tours").add("web_enterprise.test_studio_list_upsell",
    {
        test: true,
        steps: () => [
            {
                trigger: ".o_list_view",
            },
            {
                trigger: ".o_optional_columns_dropdown > button",
            },
            {
                trigger: ".o_optional_columns_dropdown .dropdown-item-studio",
                isCheck: true,
            },
        ]
    }
);
