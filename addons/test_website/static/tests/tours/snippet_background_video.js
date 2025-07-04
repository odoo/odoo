/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { VideoSelector } from "@html_editor/main/media/media_dialog/video_selector";
import { insertSnippet, registerWebsitePreviewTour } from "@website/js/tours/tour_utils";

registerWebsitePreviewTour(
    "snippet_background_video",
    {
        url: "/",
        edition: true,
    }, () => [
        {
            trigger: "body",
            run: function () {
                // Patch the VideoDialog so that it does not do external calls
                // during the test (note that we don't unpatch but as the patch
                // is only done after the execution of a test_website test, it
                // is acceptable).
                // TODO we should investigate to rather mock the external calls,
                // maybe not using a tour. Probably easier to discuss when the
                // new OWL editor will have been implemented.
                patch(VideoSelector.prototype, {
                    async prepareVimeoPreviews() {
                        // Ignore the super call and directly push a fake video
                        this.state.vimeoPreviews.push({
                            id: 1,
                            // Those lead to 404 but it's fine for the test
                            thumbnailSrc: "/hello/world.jpg",
                            src: "/hello/world.mp4",
                        });
                    },
                    async _getVideoURLData(src, options) {
                        if (src === '/hello/world.mp4') {
                            return {
                                'platform': 'vimeo',
                                'embed_url': 'about:blank',
                            };
                        }
                        return super._getVideoURLData(...arguments);
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
            trigger: ":iframe #wrap section.o_background_video > .o_bg_video_container[contenteditable=false]",
        },
    ]
);
