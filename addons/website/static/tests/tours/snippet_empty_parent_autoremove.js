odoo.define("website.tour.snippet_empty_parent_autoremove", function (require) {
"use strict";

const wTourUtils = require('website.tour_utils');

function removeSelectedBlock() {
    return {
        content: "Remove selected block",
        trigger: '#oe_snippets we-customizeblock-options:nth-last-child(3) .oe_snippet_remove',
    };
}

wTourUtils.registerWebsitePreviewTour('snippet_empty_parent_autoremove', {
    test: true,
    url: '/',
    edition: true,
}, [
    // Base case: remove both columns from text - image
    wTourUtils.dragNDrop({
        id: 's_text_image',
        name: 'Text - Image',
    }),
    {
        content: "Click on second column",
        trigger: 'iframe #wrap .s_text_image .row > :nth-child(2)',
    },
    removeSelectedBlock(),
    {
        content: "Click on first column",
        trigger: 'iframe #wrap .s_text_image .row > :first-child',
    },
    removeSelectedBlock(),
    {
        content: "Check that #wrap is empty",
        trigger: 'iframe #wrap:empty',
    },

    // Banner: test that parallax, bg-filter and shape are not treated as content
    wTourUtils.dragNDrop({
        id: 's_banner',
        name: 'Banner',
    }),
    wTourUtils.clickOnSnippet({
        id: 's_banner',
        name: 'Banner',
    }),
    {
        content: "Check that parallax is present",
        trigger: 'iframe #wrap .s_banner .s_parallax_bg',
        run: () => null,
    },
    wTourUtils.changeOption('ColoredLevelBackground', 'Shape'),
    {
        content: "Check that shape is present",
        trigger: 'iframe #wrap .s_banner .o_we_shape',
        run: () => null,
    },
    {
        content: "Click on first column",
        trigger: 'iframe #wrap .s_banner .row > :first-child',
    },
    removeSelectedBlock(),
    {
        content: "Check that #wrap is empty",
        trigger: 'iframe #wrap:empty',
        run: () => null,
    },
]);
});
