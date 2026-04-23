import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("account.additional_identifiers", {
    steps: () => [
        {
            content: "Open the 'Add identifier' dropdown",
            trigger: ".o_add_identifier_dropdown button",
            run: "click",
        },
        {
            content: "Add the DNI identifier",
            trigger: ".o_add_identifier_item[data-identifier-key='AR_DNI']",
            run: "click",
        },
        {
            content: "The DNI input is revealed and can be filled",
            trigger: "#o_additional_identifier_AR_DNI:visible",
            run: "edit 34586675",
        },
        {
            content: "Remove the DNI identifier",
            trigger: ".o_additional_identifier_field[data-identifier-key='AR_DNI'] .o_remove_identifier",
            run: "click",
        },
        {
            content: "The DNI input is hidden again after removal",
            trigger: ".o_additional_identifiers_portal:not(:has(#o_additional_identifier_AR_DNI:visible))",
        },
        {
            content: "Re-open the dropdown",
            trigger: ".o_add_identifier_dropdown button",
            run: "click",
        },
        {
            content: "The DNI identifier is offered again",
            trigger: ".o_add_identifier_item[data-identifier-key='AR_DNI']:visible",
        },
    ],
});
