import {
    clickOnEditAndWaitEditMode,
    clickOnSave,
    registerWebsitePreviewTour,
    changeOptionInPopover,
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
        ...changeOptionInPopover("Field", "Visibility", "Visible only if"),
        {
            content: "Open model selector",
            trigger: "button[id='hidden_condition_record_opt']:contains('Test Tag')",
            run: "click",
        },
        {
            content: "Set model to tag #2",
            trigger: ".o_popover div.o-dropdown-item:contains('Test Tag #2')",
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
            trigger: "button[id='hidden_condition_record_opt']:contains('Is equal to')",
            run: "click",
        },
        {
            content: "Set comparator to Is not equal",
            trigger: ".o_popover div.o-dropdown-item:contains('Is not equal to')",
            run: "click",
        },
        ...clickOnSave(),
        {
            content: "Name field is shown",
            trigger: ":iframe .s_website_form:has(.s_website_form_field_hidden_if:not(.d-none))",
        },
    ],
);
