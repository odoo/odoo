import {
    clickOnEditAndWaitEditMode,
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
            "[data-container-title='Specifications'] [data-label='Add Field'] .o-hb-select-toggle",
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
            ":iframe tr[data-extra-field-id]:has(td:contains('Internal Reference')) td:contains('SOFA-REF')",
    },
]);
