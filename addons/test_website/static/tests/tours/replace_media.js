import { patch } from "@web/core/utils/patch";
import { VideoSelector } from "@html_editor/main/media/media_dialog/video_selector";
import {
    changeOption,
    insertSnippet,
    registerWebsitePreviewTour,
} from '@website/js/tours/tour_utils';

const VIDEO_URL = 'https://www.youtube.com/watch?v=Dpq87YCHmJc';

/**
 * The purpose of this tour is to check the media replacement flow.
 */
registerWebsitePreviewTour('test_replace_media', {
    url: '/',
    edition: true,
}, () => [
    {
        trigger: "body",
        run: function () {
            // Patch the VideoDialog so that it does not do external calls
            // during the test (note that we don't unpatch but as the patch
            // is only done after the execution of a test_website test and
            // specific to an URL only, it is acceptable).
            // TODO if we ever give the possibility to upload its own videos,
            // this won't be necessary anymore.
            patch(VideoSelector.prototype, {
                async _getVideoURLData(src, options) {
                    if (src === VIDEO_URL || src === 'about:blank') {
                        let resultUrl = 'about:blank'
                        // Only autoplay handled here for simplicity
                        if(options.autoplay) {
                            resultUrl += "?autoplay=1"
                        }
                        return {platform: 'youtube', embed_url: resultUrl};
                    }
                    if (src === 'about:blank?autoplay=1') {
                        return {platform: 'youtube', embed_url: src};
                    }
                    return super._getVideoURLData(...arguments);
                },
            });
            // Prevents the VideoSelector from adding 'https:' before
            // 'about:blank', which makes the URL invalid for URL.canParse
            patch(VideoSelector.prototype, {
                async syncOptionsWithUrl() {
                    if(this.state.urlInput.startsWith("https:about:blank")) {
                        this.state.urlInput = this.state.urlInput.substring(6);
                    }
                    super.syncOptionsWithUrl();
                }
            })
        },
    },
    ...insertSnippet({
        name: 'Title - Image',
        id: 's_picture',
        groupName: "Images",
    }),
    {
        content: "select image",
        trigger: ":iframe .s_picture figure img",
        run: "click",
    },
    {
        content: "ensure image size is displayed",
        trigger: ".o_customize_tab [data-container-title='Image'] .options-container-header:contains('kb')",
    },
    changeOption("Image", "[data-label='Shape'] .dropdown-toggle"),
    {
        content: "Click on the first image shape",
        trigger: "button[data-action-id='setImageShape']",
        run: "click",
    },
    {
        content: "Open MediaDialog from an image",
        trigger: "button[data-action-id='replaceMedia']",
        run: "click",
    },
    {
        content: "select svg",
        trigger: ".o_select_media_dialog .o_button_area[aria-label='sample.svg']",
        run: "click",
    },
    {
        content: "ensure the svg does have a shape",
        trigger: ":iframe .s_picture figure img[data-shape]",
    },
    {
        content: "ensure image size is displayed",
        trigger: ".o_customize_tab [data-container-title='Image'] span[title='Size']",
    },
    {
        content: "replace image",
        trigger: "button[data-action-id='replaceMedia']",
        run: "click",
    },
    {
        content: "go to pictogram tab",
        trigger: ".o_select_media_dialog .nav-link:contains('Icons')",
        run: "click",
    },
    {
        content: "select an icon",
        trigger: ".o_select_media_dialog:has(.nav-link.active:contains('Icons')) .tab-content span.fa-heart",
        run: "click",
    },
    {
        content: "ensure icon block is displayed",
        trigger: ".o_customize_tab [data-container-title='Icon']",
    },
    {
        content: "select footer",
        trigger: ":iframe footer",
        run: "click",
    },
    {
        content: "select icon",
        trigger: ":iframe .s_picture figure span.fa-heart",
        run: "click",
    },
    {
        content: "ensure icon block is still displayed",
        trigger: ".o_customize_tab [data-container-title='Icon']",
    },
    {
        content: "replace icon",
        trigger: "button[data-action-id='replaceMedia']",
        run: "click",
    },
    {
        content: "go to video tab",
        trigger: ".o_select_media_dialog .nav-link:contains('Video')",
        run: "click",
    },
    {
        content: "enter a video URL",
        trigger: ".o_select_media_dialog #o_video_text",
        // Design your first web page.
        run: `edit ${VIDEO_URL}`,
    },
    {
        content: "wait for preview to appear",
        // "about:blank" because the VideoWidget was patched at the start of this tour
        trigger: ".o_select_media_dialog div.media_iframe_video [src='about:blank']:iframe body",
    },
    {
        content: "enable auto-play",
        trigger: ".o_video_dialog_options label.o_switch",
        run: "click",
    },
    {
        content: "confirm selection",
        trigger: ".o_select_media_dialog .modal-footer .btn-primary",
        run: "click",
    },
    {
        content: "ensure video option block is displayed",
        trigger: ".o_customize_tab [data-container-title='Video']",
    },
    {
        content: "replace image",
        trigger: ".btn-success[data-action-id='replaceMedia']",
        run: "click",
    },
    {
        content: "check that autoplay is still enabled",
        trigger: ".o_video_dialog_options label.o_switch",
        run: () => {
            const input = document.querySelector(".o_video_dialog_options label.o_switch input");
            if(!input.value) {
                throw new Error("Autoplay should be enabled");
            }
        },
    },
    {
        content: "go to pictogram tab",
        trigger: ".o_select_media_dialog .nav-link:contains('Icons')",
        run: "click",
    },
    {
        content: "select an icon",
        trigger: ".o_select_media_dialog:has(.nav-link.active:contains('Icons')) .tab-content span.fa-heart",
        run: "click",
    },
    {
        content: "ensure icon block is displayed",
        trigger: ".o_customize_tab [data-container-title='Icon']",
    },
    {
        content: "select footer",
        trigger: ":iframe footer",
        run: "click",
    },
    {
        content: "select icon",
        trigger: ":iframe .s_picture figure span.fa-heart",
        run: "click",
    },
    {
        content: "ensure icon block is still displayed",
        trigger: ".o_customize_tab [data-container-title='Icon']",
    },
]);
