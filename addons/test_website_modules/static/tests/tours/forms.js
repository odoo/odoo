import { registry } from "@web/core/registry";
import {
    changeOption,
    clickOnSave,
    insertSnippet,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

registerWebsitePreviewTour(
    "make_email_field_non_required",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...insertSnippet({
            id: "s_title_form",
            name: "Contact & Forms",
            groupName: "Contact & Forms",
        }),
        {
            content: "Click inside the form to open form options",
            trigger: ":iframe .s_website_form",
            run: "click",
        },
        {
            content: "Click on the action option",
            trigger: "div:has(>span:contains('Action')) + div button",
            run: "click",
        },
        {
            content: "Change the form action",
            trigger: "div.o-dropdown-item:contains('Create a Customer')",
            run: "click",
        },
        // Turn off the Required field option
        changeOption("Field", "[data-action-id='toggleRequired'] input"),
        {
            content: "Check mail field made non-required",
            trigger:
                ":iframe .s_website_form form.o_website_form_copy_enabled .s_website_form_field.s_website_form_copy_email[data-type='email']:not(.s_website_form_required)",
        },
        ...clickOnSave(),
    ]
);

registry.category("web_tour.tours").add("submit_form_without_email", {
    url: "/",
    steps: () => [
        {
            content: "Fill in the name",
            trigger: "input[name='name']",
            run: "edit Test Name",
        },
        {
            content: "Click to submit the form",
            trigger: ".s_website_form_send",
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "Check the form was submitted without errors",
            trigger: "#wrap:has(h1:contains('Thank You!'))",
        },
    ],
});
