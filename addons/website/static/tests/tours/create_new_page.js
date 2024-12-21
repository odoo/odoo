import { clickOnSave, registerWebsitePreviewTour } from "@website/js/tours/tour_utils";

registerWebsitePreviewTour(
    "website_create_new_page",
    {
        test: true,
        url: "/",
    },
    () => [
        {
            content: "Open create content menu",
            trigger: ".o_new_content_container a",
            run: "click",
        },
        {
            content: "Create a new page",
            trigger: 'a[title="New Page"]',
            run: "click",
        },
        {
            content: "Use blank template",
            trigger: ".o_page_template button",
            run: "click",
        },
        {
            content: "Name page",
            trigger: ".modal-body input",
            run: "edit New Page",
        },
        {
            content: "Don't add to menu",
            trigger: ".modal-body .o_switch",
            run: "click",
        },
        {
            content: "Click on Create button",
            trigger: ".modal-footer .btn-primary",
            run: "click",
        },
        {
            content: "Wait for editor to open",
            trigger: ".o_website_navbar_hide",
        },
        ...clickOnSave(),
    ],
);
