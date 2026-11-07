import { registerWebsitePreviewTour } from "@website/js/tours/tour_utils";

registerWebsitePreviewTour(
    "website_preview_breadcrumb",
    {
        url: "/test_model/1",
    },
    () => [
        {
            content: "Navigate to another page inside the iframe",
            trigger: ":iframe a#test_link_to_second",
            run: "click",
        },
        {
            content: "Wait for the second record page",
            trigger: ':iframe span[data-oe-expression="test_model.name"]:contains("Second Record")',
        },
        {
            content: "Go to the backend",
            trigger: ".o_menu_systray .o_website_edit_in_backend a",
            run: "click",
        },
        {
            content: "Check the second record form is opened",
            trigger: ".o_form_view .o_field_widget[name=name] input:value(Second Record)",
        },
        {
            content: "Go back to the website preview through the breadcrumb",
            trigger: ".o_breadcrumb .o_back_button",
            run: "click",
        },
        {
            content: "Check we are back on the last visited page, not the initial one",
            trigger: ':iframe span[data-oe-expression="test_model.name"]:contains("Second Record")',
        },
    ]
);
