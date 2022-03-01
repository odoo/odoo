/** @odoo-module **/

import wTourUtils from 'website.tour_utils';

/**
 * The purpose of this tour is to check the media replacement flow.
 */
wTourUtils.registerEditionTour('test_replace_media', {
    url: '/',
    test: true,
}, [
    wTourUtils.clickOnEdit(),
    {
        content: "drop picture snippet",
        trigger: "#oe_snippets .oe_snippet[name='Picture'] .oe_snippet_thumbnail:not(.o_we_already_dragging)",
        extra_trigger: ".editor_enable.editor_has_snippets",
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
]);
