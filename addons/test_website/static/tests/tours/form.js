import {
    clickOnEditAndWaitEditMode,
    clickOnSave,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

registerWebsitePreviewTour(
    "test_form_conditional_visibility_record_field",
    {
        url: "/test_website/model_item/1",
        edition: true,
    },
    () => [
        {
            content: "Select name field",
            trigger: ":iframe .s_website_form .s_website_form_input[name=name]",
            run: "click",
        },
        {
            content: "Open visibility dropdown",
            trigger: 'we-select:has([data-set-visibility="conditional"])',
            run: "click",
        },
        {
            content: "Set visibility to conditional",
            trigger: '[data-set-visibility="conditional"]',
            run: "click",
        },
        {
            content: "Open model selector",
            trigger: 'we-select:has([data-select-data-attribute="2"])',
            run: "click",
        },
        {
            content: "Set model to tag #2",
            trigger: '[data-select-data-attribute="2"]',
            run: "click",
        },
        ...clickOnSave(),
        {
            content: "Name field is hidden",
            trigger: ":iframe .s_website_form:has(.s_website_form_field_hidden_if.d-none)",
        },
        ...clickOnEditAndWaitEditMode(),

        {
            content: "Select name field",
            trigger: ":iframe .s_website_form .s_website_form_input[name=name]",
            run: "click",
        },
        {
            content: "Open comparator dropdown",
            trigger: 'we-select:has([data-select-data-attribute="!selected"])',
            run: "click",
        },
        {
            content: "Set comparator to Is not equal",
            trigger: '[data-select-data-attribute="!selected"]',
            run: "click",
        },
        ...clickOnSave(),
        {
            content: "Name field is shown",
            trigger: ":iframe .s_website_form:has(.s_website_form_field_hidden_if:not(.d-none))",
        },
    ],
);
