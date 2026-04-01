/** @odoo-module **/
import {
    clickOnEditAndWaitEditMode,
    clickOnSave,
    insertSnippet,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

registerWebsitePreviewTour(
    "website_seo_notification",
    {
        url: "/",
    },
    () => [
        // Part one checks that the SEO notification is displayed when the page title is not set.
        {
            content: "Open new page menu",
            trigger: ".o_menu_systray .o_new_content_container > button",
            run: "click",
        },
        {
            content: "Click on new page",
            trigger: "button.o_new_content_element",
            run: "click",
        },
        {
            content: "Click on Use this template",
            trigger: ".o_page_template .o_button_area:not(:visible)",
            run: "click",
        },
        {
            content: "Insert page name",
            trigger:
                ".modal:not(.o_inactive_modal):contains(new page) .modal-body input[type=text]",
            run: "edit Test Page",
        },
        {
            trigger: "input[type='text']:value(Test Page)",
        },
        {
            content: "Create page",
            trigger:
                ".modal:not(.o_inactive_modal):contains(new page) button.btn-primary:contains(create)",
            run: "click",
        },
        ...insertSnippet({
            id: "s_text_image",
            name: "Text - Image",
            groupName: "Content",
        }),
        ...clickOnSave(),
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
            trigger:
                ":iframe #o_main_nav .navbar-nav .dropdown.o_no_autohide_item > a.dropdown-toggle",
            run: "click",
        },
        {
            content: "Click on My Account",
            trigger: ":iframe #o_main_nav .js_usermenu a.dropdown-item.ps-3:contains('My Account')",
            run: "click",
        },
        {
            content: "Let the page get loaded",
            trigger: ":iframe .o_portal",
        },
        ...clickOnEditAndWaitEditMode(),
        ...insertSnippet({
            id: "s_text_image",
            name: "Text - Image",
            groupName: "Content",
        }),
        ...clickOnSave(),
        {
            content: "Check the SEO notification should not be displayed",
            trigger: "body:not(:has(.o_notification_manager .o_notification))",
        },
    ]
);
