import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("account.portal_additional_identifiers", {
    steps: () => [
        {
            content: "Open the 'Add identifier' dropdown",
            trigger: ".o_add_identifier_dropdown button",
            run: "click",
        },
        {
            content: "Add the NIR identifier",
            trigger: ".o_add_identifier_item[data-identifier-key='FR_CN']",
            run: "click",
        },
        {
            content: "The NIR input is revealed and can be filled",
            trigger: "#o_additional_identifier_FR_CN:visible",
            run: "edit 295109912611193",
        },
        {
            content: "Remove the NIR identifier",
            trigger: ".o_additional_identifier_field[data-identifier-key='FR_CN'] .o_remove_identifier",
            run: "click",
        },
        {
            content: "The NIR input is hidden again after removal",
            trigger: ".o_additional_identifiers_portal:not(:has(#o_additional_identifier_FR_CN:visible))",
        },
        {
            content: "Re-open the dropdown",
            trigger: ".o_add_identifier_dropdown button",
            run: "click",
        },
        {
            content: "The NIR identifier is offered again",
            trigger: ".o_add_identifier_item[data-identifier-key='FR_CN']:visible",
        },
    ],
});
