/** @odoo-module */

import wTourUtils from "@website/js/tours/tour_utils";

wTourUtils.registerWebsitePreviewTour("snippet_image_crop", {
    test: true,
    url: "/",
    edition: true,
}, () => [
    wTourUtils.dragNDrop({
        id: "s_text_image",
        name: "Text - Image",
    }),
    {
        content: "Select image",
        trigger: "iframe .s_text_image img",
    },
    {
        content: "Replace image",
        trigger: "iframe .s_text_image img",
        run: "dblclick",
    },
    {
        content: "Search for the illustration images",
        trigger: ".o_select_media_dialog .o_we_search",
        run: "text city",
    },
    {
        content: "Select the first illustration image",
        trigger: ".o_we_existing_attachments a.o_we_media_author"
    },
    {
        content: "Click on the first illustration image",
        trigger: ".o_select_media_dialog .o_we_attachment_highlight",
    },
    {
        content: "Select the image",
        trigger: "iframe .s_text_image img",
        ischeck: true,
    },
    {
        content: "Try to crop the image",
        trigger: "#oe_snippets .o_we_customize_panel .o_we_user_value_widget[data-crop='true']",
    },
    {
        content: "Observe the crop is denied for illustration image",
        trigger: "body:has('.o_notification_manager .o_notification')",
    },
    ...wTourUtils.clickOnSave(),
]);
