/** @odoo-module */
import wTourUtils from "website.tour_utils";

wTourUtils.registerWebsitePreviewTour(
    "website_media_iframe_video",
    {
        test: true,
        url: "/",
        edition: true,
    },
    [
        wTourUtils.dragNDrop({
            id: "s_text_image",
            name: "Text - Image",
        }),
        {
            content: "Select the image",
            trigger: "iframe #wrap .s_text_image img",
        },
        {
            content: "Open image link options",
            trigger: "[data-name='media_link_opt']",
        },
        {
            content: "Enter the url",
            trigger: "input[placeholder='www.example.com']",
            run: "text odoo.com",
        },
        {
            content: "Click on replace media",
            trigger: "[data-replace-media='true']",
        },
        {
            content: "Click on video button",
            trigger: "a:contains('Videos')",
        },
        {
            content: "Enter video link",
            trigger: "#o_video_text",
            run: "text https://youtu.be/nbso3NVz3p8",
        },
        {
            content: "Check video is preview",
            trigger: ".o_video_dialog_iframe",
            run: () => {}, // This is a check.
        },
        {
            content: "Click on 'add' button",
            trigger: ".modal-footer button:contains('Add')",
        },
        {
            content: "Ensure that the parent of media_iframe_video is not an 'a' tag.",
            trigger: "iframe .media_iframe_video",
            run: function () {
                if (this.$anchor[0].parentElement.tagName === "A") {
                    console.error("Iframe video has link!!!");
                }
            },
        },
    ]
);

wTourUtils.registerWebsitePreviewTour(
    "website_snippet_background_video",
    {
        test: true,
        url: "/",
        edition: true,
    },
    [
        wTourUtils.dragNDrop({
            id: "s_text_block",
            name: "Text",
        }),
        {
            content: "Click on the text block.",
            trigger: "iframe #wrap section.s_text_block",
        },
        {
            content: "Click on the 'Background Video' button option.",
            trigger: "we-button[data-name='bg_video_toggler_opt']",
        },
        {
            content: "Click on the first sample video in the modal.",
            trigger: "#video-suggestion .o_sample_video",
        },
        {
            content: "Check the video is select.",
            trigger: "textarea.is-valid",
            run: () => {}, // This is a check.
        },
        {
            content: "Click on the 'Add' button to apply the selected video as the background.",
            trigger: ".modal-footer button.btn-primary",
        },
        {
            content: "Verify that the video is set as the background of the snippet.",
            trigger: "iframe #wrap section.o_background_video",
        },
    ]
);
