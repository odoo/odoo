/** @odoo-module **/

import tour from 'web_tour.tour';

/**
 * The purpose of this tour is to check the media replacement flow.
 */
tour.register('test_replace_media', {
    url: '/',
    test: true
}, [
    {
        content: "enter edit mode",
        trigger: "a[data-action=edit]"
    },
    {
        content: "drop picture snippet",
        trigger: "#oe_snippets .oe_snippet[name='Picture'] .oe_snippet_thumbnail:not(.o_we_already_dragging)",
        extra_trigger: "body.editor_enable.editor_has_snippets",
        moveTrigger: ".oe_drop_zone",
        run: "drag_and_drop #wrap",
    },
    {
        content: "select image",
        trigger: "#wrapwrap .s_picture figure img",
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
        trigger: ".o_select_media_dialog .nav-link#editor-media-icon-tab",
    },
    {
        content: "select an icon",
        trigger: ".o_select_media_dialog .tab-pane#editor-media-icon span.fa-lemon-o",
    },
    {
        content: "ensure icon block is displayed",
        trigger: "#oe_snippets we-customizeblock-options we-title:contains('Icon')",
        run: function () {}, // check
    },
    {
        content: "select footer",
        trigger: "#wrapwrap footer",
    },
    {
        content: "select icon",
        trigger: "#wrapwrap .s_picture figure span.fa-lemon-o",
    },
    {
        content: "ensure icon block is still displayed",
        trigger: "#oe_snippets we-customizeblock-options we-title:contains('Icon')",
        run: function () {}, // check
    },
]);
