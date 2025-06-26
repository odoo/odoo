/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { VideoSelector } from '@web_editor/components/media_dialog/video_selector';
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
                        return {platform: 'youtube', embed_url: 'about:blank'};
                    }
                    return super._getVideoURLData(...arguments);
                },
            });
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
        trigger: "#oe_snippets we-title:contains('Image') .o_we_image_weight:contains('kb')",
    },
    changeOption("ImageTools", 'we-select[data-name="shape_img_opt"] we-toggler'),
    changeOption("ImageTools", "we-button[data-set-img-shape]"),
    {
        content: "replace image",
        trigger: "#oe_snippets we-button[data-replace-media]",
        run: "click",
    },
    {
        content: "select svg",
        trigger: ".o_select_media_dialog img[title='sample.svg']",
        run: "click",
    },
    {
        content: "ensure the svg doesn't have a shape",
        trigger: ":iframe .s_picture figure img:not([data-shape])",
    },
    {
        content: "ensure image size is not displayed",
        trigger: "#oe_snippets we-title:contains('Image'):not(:has(.o_we_image_weight:visible))",
    },
    {
        content: "replace image",
        trigger: "#oe_snippets we-button[data-replace-media]",
        run: "click",
    },
    {
        content: "go to pictogram tab",
        trigger: ".o_select_media_dialog .nav-link:contains('Icons')",
        run: "click",
    },
    {
        content: "select an icon",
        trigger: ".o_select_media_dialog:has(.nav-link.active:contains('Icons')) .tab-content span.fa-lemon-o",
        run: "click",
    },
    {
        content: "ensure icon block is displayed",
        trigger: "#oe_snippets we-customizeblock-options we-title:contains('Icon')",
    },
    {
        content: "select footer",
        trigger: ":iframe footer",
        run: "click",
    },
    {
        content: "select icon",
        trigger: ":iframe .s_picture figure span.fa-lemon-o",
        run: "click",
    },
    {
        content: "ensure icon block is still displayed",
        trigger: "#oe_snippets we-customizeblock-options we-title:contains('Icon')",
    },
    {
        content: "replace icon",
        trigger: "#oe_snippets we-button[data-replace-media]",
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
        content: "confirm selection",
        trigger: ".o_select_media_dialog .modal-footer .btn-primary",
        run: "click",
    },
    {
        content: "ensure video option block is displayed",
        trigger: "#oe_snippets we-customizeblock-options we-title:contains('Video')",
    },
    {
        content: "replace image",
        trigger: "#oe_snippets we-button[data-replace-media]",
        run: "click",
    },
    {
        content: "go to pictogram tab",
        trigger: ".o_select_media_dialog .nav-link:contains('Icons')",
        run: "click",
    },
    {
        content: "select an icon",
        trigger: ".o_select_media_dialog:has(.nav-link.active:contains('Icons')) .tab-content span.fa-lemon-o",
        run: "click",
    },
    {
        content: "ensure icon block is displayed",
        trigger: "#oe_snippets we-customizeblock-options we-title:contains('Icon')",
    },
    {
        content: "select footer",
        trigger: ":iframe footer",
        run: "click",
    },
    {
        content: "select icon",
        trigger: ":iframe .s_picture figure span.fa-lemon-o",
        run: "click",
    },
    {
        content: "ensure icon block is still displayed",
        trigger: "#oe_snippets we-customizeblock-options we-title:contains('Icon')",
    },
]);
