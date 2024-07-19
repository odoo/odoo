import wTourUtils from "@website/js/tours/tour_utils";

wTourUtils.registerWebsitePreviewTour(
    "website_seo_notification",
    {
        test: true,
        url: "/",
    },
    () => [
        // Part one checks that the SEO notification is displayed when the page title is not set.
        {
            content: "Open new page menu",
            trigger: ".o_menu_systray .o_new_content_container > a",
            run: "click",
        },
        {
            content: "Click on new page",
            trigger: ".o_new_content_element a",
            run: "click",
        },
        {
            content: "Click on Use this template",
            trigger: ".o_page_template button.btn-primary",
            run: "click",
        },
        {
            content: "Insert page name",
            trigger: ".modal .modal-dialog .modal-body input[type='text']",
            in_modal: false,
            run: "edit Test Page",
        },
        {
            trigger: "input[type='text']:value(Test Page)",
        },
        {
            content: "Create page",
            trigger: ".modal button.btn-primary:contains(create)",
            in_modal: false,
            run: "click",
        },
        ...wTourUtils.dragNDrop({ id: "s_text_image", name: "Text - Image" }),
        ...wTourUtils.clickOnSave(),
        {
            content: "Publish your website",
            trigger: ".o_menu_systray_item.o_website_publish_container a",
            run: "click",
        },
        {
            content: "Check the SEO notification is displayed",
            trigger: ".o_notification_manager .o_notification:contains('Page title not set.')",
        },
        {
            trigger: "body:not(:has(.o_notification_manager .o_notification))",
        },

        // Part 2 checks that the SEO notification is not displayed when we are in any page like /my or /shop etc.
        {
            content: "Open the dropdown menu",
            trigger: ":iframe #o_main_nav .navbar-nav .dropdown.o_no_autohide_item > a.dropdown-toggle",
            run: "click",
        },
        {
            content: "Click on My Account",
            trigger: ":iframe #o_main_nav .js_usermenu a.dropdown-item.ps-3:contains('My Account')",
            run: "click",
        },

        ...wTourUtils.clickOnEditAndWaitEditMode(),
        ...wTourUtils.dragNDrop({ id: "s_text_image", name: "Image - Text" }),

        {
            content: "Check the SEO notification should not be displayed",
            trigger: "body:not(:has(.o_notification_manager .o_notification))",
        },
    ]
);
