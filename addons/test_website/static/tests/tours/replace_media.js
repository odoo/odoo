/** @odoo-module **/

import { patch } from '@web/core/utils/patch';
import { VideoSelector } from '@web_editor/components/media_dialog/video_selector';
import wTourUtils from 'website.tour_utils';

const VIDEO_URL = 'https://www.youtube.com/watch?v=Dpq87YCHmJc';

/**
 * The purpose of this tour is to check the media replacement flow.
 */
wTourUtils.registerWebsitePreviewTour('test_replace_media', {
    url: '/',
    test: true,
}, [
    wTourUtils.clickOnEdit(),
    {
        trigger: '.editor_enable.editor_has_snippets',
        run: function () {
            // Patch the VideoDialog so that it does not do external calls
            // during the test (note that we don't unpatch but as the patch
            // is only done after the execution of a test_website test and
            // specific to an URL only, it is acceptable).
            // TODO if we ever give the possibility to upload its own videos,
            // this won't be necessary anymore.
            patch(VideoSelector.prototype, "Video selector patch", {
                async _getVideoURLData(src, options) {
                    if (src === VIDEO_URL || src === 'about:blank') {
                        return {platform: 'youtube', embed_url: 'about:blank'};
                    }
                    return this._super(...arguments);
                },
            });
        },
    },
    {
        content: "drop picture snippet",
        trigger: "#oe_snippets .oe_snippet[name='Picture'] .oe_snippet_thumbnail:not(.o_we_already_dragging)",
        moveTrigger: "iframe .oe_drop_zone",
        run: "drag_and_drop iframe #wrap",
    },
    {
        content: "select image",
        trigger: "iframe .s_picture figure img",
    },
    {
        content: "ensure image size is displayed",
        trigger: "#oe_snippets we-title:contains('Image') .o_we_image_weight:contains('kb')",
        run: function () {}, // check
    },
    {
        content: "replace image",
        trigger: "#oe_snippets we-button[data-replace-media]",
    },
    {
        content: "select svg",
        trigger: ".o_select_media_dialog img[title='sample.svg']",
    },
    {
        content: "ensure image size is not displayed",
        trigger: "#oe_snippets we-title:contains('Image'):not(:has(.o_we_image_weight:visible))",
        run: function () {}, // check
    },
    {
        content: "replace image",
        trigger: "#oe_snippets we-button[data-replace-media]",
    },
    {
        content: "go to pictogram tab",
        trigger: ".o_select_media_dialog .nav-link:contains('Icons')",
    },
    {
        content: "select an icon",
        trigger: ".o_select_media_dialog:has(.nav-link.active:contains('Icons')) .tab-content span.fa-lemon-o",
    },
    {
        content: "ensure icon block is displayed",
        trigger: "#oe_snippets we-customizeblock-options we-title:contains('Icon')",
        run: function () {}, // check
    },
    {
        content: "select footer",
        trigger: "iframe footer",
    },
    {
        content: "select icon",
        trigger: "iframe .s_picture figure span.fa-lemon-o",
    },
    {
        content: "ensure icon block is still displayed",
        trigger: "#oe_snippets we-customizeblock-options we-title:contains('Icon')",
        run: function () {}, // check
    },
    {
        content: "replace icon",
        trigger: "#oe_snippets we-button[data-replace-media]",
    },
    {
        content: "go to video tab",
        trigger: ".o_select_media_dialog .nav-link:contains('Video')",
    },
    {
        content: "enter a video URL",
        trigger: ".o_select_media_dialog #o_video_text",
        // Design your first web page.
        run: `text ${VIDEO_URL}`,
    },
    {
        content: "wait for preview to appear",
        // "about:blank" because the VideoWidget was patched at the start of this tour
        trigger: ".o_select_media_dialog div.media_iframe_video iframe[src='about:blank']",
        run: function () {}, // check
    },
    {
        content: "confirm selection",
        trigger: ".o_select_media_dialog .modal-footer .btn-primary",
    },
    {
        content: "ensure video option block is displayed",
        trigger: "#oe_snippets we-customizeblock-options we-title:contains('Video')",
        run: function () {}, // check
    },
    {
        content: "replace image",
        trigger: "#oe_snippets we-button[data-replace-media]",
    },
    {
        content: "go to pictogram tab",
        trigger: ".o_select_media_dialog .nav-link:contains('Icons')",
    },
    {
        content: "select an icon",
        trigger: ".o_select_media_dialog:has(.nav-link.active:contains('Icons')) .tab-content span.fa-lemon-o",
    },
    {
        content: "ensure icon block is displayed",
        trigger: "#oe_snippets we-customizeblock-options we-title:contains('Icon')",
        run: function () {}, // check
    },
    {
        content: "select footer",
        trigger: "iframe footer",
    },
    {
        content: "select icon",
        trigger: "iframe .s_picture figure span.fa-lemon-o",
    },
    {
        content: "ensure icon block is still displayed",
        trigger: "#oe_snippets we-customizeblock-options we-title:contains('Icon')",
        run: function () {}, // check
    },
]);
