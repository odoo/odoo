/** @odoo-module **/

import { insertSnippet, registerWebsitePreviewTour } from "@website/js/tours/tour_utils";
import { patch } from "@web/core/utils/patch";
import { Vimeo } from "@html_editor/main/media/video/providers/vimeo";

let unpatchThumbnailUrl;
registerWebsitePreviewTour(
    "snippet_background_video",
    {
        edition: true,
    },
    () => [
        {
            // Avoid fetch error on the runbot.
            content: " patch the thumbnail url getter",
            trigger: "body",
            run: () => {
                unpatchThumbnailUrl = patch(Vimeo, {
                    getThumbnailUrl(videoId) {
                        return "/web/image/mock-thumbnail-url-" + videoId;
                    },
                });
            },
        },
        ...insertSnippet({
            id: "s_text_block",
            name: "Text",
            groupName: "Text",
        }),
        {
            content: "Click on the text block.",
            trigger: ":iframe #wrap section.s_text_block",
            run: "click",
        },
        {
            content: "Click on the 'Background Video' button option.",
            trigger: "button[data-action-id='toggleBgVideo']",
            run: "click",
        },
        {
            content: "Click on the first sample video in the modal.",
            trigger: "#video-suggestion .o_sample_video",
            run: "click",
        },
        {
            content: "Check the video is select.",
            trigger: "textarea.is-valid",
        },
        {
            content: "Click on the 'Add' button to apply the selected video as the background.",
            trigger: ".modal-footer button.btn-primary",
            run: "click",
        },
        {
            content: "Verify that the video is set as the background of the snippet.",
            trigger: ":iframe #wrap section.o_background_video",
        },
        {
            content: "Check that the video container is not editable.",
            trigger:
                ":iframe #wrap section.o_background_video > .o_bg_video_container[contenteditable=false]",
        },
        {
            trigger: "body",
            run: () => unpatchThumbnailUrl(),
        },
    ]
);
