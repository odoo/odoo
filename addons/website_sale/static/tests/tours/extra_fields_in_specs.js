import {
    clickOnEditAndWaitEditMode,
    clickOnSave,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

registerWebsitePreviewTour("website_sale_add_extra_field", {}, () => [
    ...clickOnEditAndWaitEditMode(),
    {
        content: "Select the product specifications",
        trigger: ":iframe .o_wsale_specs",
        run: "click",
    },
    {
        content: "Open the extra field selector",
        trigger:
            "[data-container-title='Specifications'] [data-label='Add Field'] .o_hb_select_toggle",
        run: "click",
    },
    {
        content: "Select the internal reference field",
        trigger:
            ".o_popover [data-action-id='selectExtraField']:contains('Internal Reference')",
        run: "click",
    },
    {
        content: "Add the selected field",
        trigger: "[data-action-id='addExtraField']:contains('Confirm')",
        run: "click",
    },
    {
        content: "Check that the extra field is displayed",
        trigger:
            ":iframe .o_wsale_extra_field:has(td:contains('Internal Reference')) td:contains('SOFA-RED')",
    },
    ...clickOnSave(),
    {
        content: "Switch to the blue variant",
        trigger: ":iframe input.js_variant_change[data-value-name='blue']",
        run: "click",
    },
    {
        content: "Check that the specifications show the blue variant's values",
        trigger: ":iframe .o_wsale_specs tr:has(td:contains('Color')) td:contains('blue')",
    },
    {
        content: "Check that the extra field shows the blue variant's value",
        trigger:
            ":iframe .o_wsale_extra_field:has(td:contains('Internal Reference')) td:contains('SOFA-BLUE')",
    },
]);
