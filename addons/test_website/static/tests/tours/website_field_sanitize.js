/** @odoo-module */

import tour from "web_tour.tour";

// As admin, add a YouTube video iframe in a `sanitize_overridable` HTML field. 
tour.register("website_designer_iframe_video", {
    test: true,
}, [{
        content: "Open the media dialog to add a video",
        trigger: "iframe .fa-heart",
        run: "dblclick",
    },
    {
        content: 'Go to the "Videos" tab in the media dialog',
        trigger: ".o_select_media_dialog .o_notebook_headers .nav-item a:contains('Videos')",
    },
    {
        content: "Add a YouTube video",
        trigger: ".o_select_media_dialog #o_video_text",
        run: "text //www.youtube.com/embed/G8b4UZIcTfg",
    },
    {
        content: "Save and close the media dialog",
        extra_trigger: ".modal .o_video_preview .media_iframe_video iframe[src*='G8b4UZIcTfg']",
        trigger: ".modal-footer .btn-primary",
    },
    {
        content: "Save changes",
        trigger: 'button[data-action="save"]',
    },
    {
        content: "Check that the video was correctly saved",
        trigger: "iframe .media_iframe_video[data-oe-expression*='G8b4UZIcTfg']",
        run: () => {},
    },
]);

// Check that a restricted editor can edit the field content (event with a video iframe).
tour.register("website_restricted_editor_iframe_video", {
    test: true,
}, [{
        content: "Check that the video iframe was correctly restored after saving the changes",
        trigger: "iframe [data-oe-field]:not([data-oe-sanitize-prevent-edition]) .media_iframe_video[data-oe-expression*='G8b4UZIcTfg']",
        run: () => {},
    },
    {
        content: "As a restricted editor, edit the HTML field content",
        trigger: "iframe .o_test_website_description",
        run: "text I can still edit the HTML field",
    },
    {
        content: "Save changes",
        trigger: 'button[data-action="save"]',
    },
    {
        content: "Check that the HTML content (with a video iframe) was correctly updated",
        trigger: "iframe .o_test_website_description:contains('I can still edit the HTML field')",
        run: () => {},
    },
]);
