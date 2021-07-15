odoo.define("website.tour.snippet_empty_parent_autoremove", function (require) {
"use strict";

const tour = require('web_tour.tour');
const wTourUtils = require('website.tour_utils');

function removeSelectedBlock() {
    return {
        content: "Remove selected block",
        trigger: '#oe_snippets we-customizeblock-options:last-child .oe_snippet_remove',
    };
}

tour.register('snippet_empty_parent_autoremove', {
    test: true,
    url: '/?enable_editor=1',
}, [
    // Base case: remove both columns from text - image
    wTourUtils.dragNDrop({
        id: 's_text_image',
        name: 'Text - Image',
    }),
    {
        content: "Click on second column",
        trigger: '#wrap .s_text_image .row > :nth-child(2)',
    },
    removeSelectedBlock(),
    {
        content: "Click on first column",
        trigger: '#wrap .s_text_image .row > :first-child',
    },
    removeSelectedBlock(),
    {
        content: "Check that #wrap is empty",
        trigger: '#wrap:empty',
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
        trigger: '#wrap .s_banner .s_parallax_bg',
        run: () => null,
    },
    wTourUtils.changeOption('ColoredLevelBackground', 'Shape'),
    {
        content: "Check that shape is present",
        trigger: '#wrap .s_banner .o_we_shape',
        run: () => null,
    },
    wTourUtils.changeOption('ColoredLevelBackground', 'Filter'),
    {
        content: "Check that background-filter is present",
        trigger: '#wrap .s_banner .o_we_bg_filter',
        run: () => null,
    },
    {
        content: "Click on first column",
        trigger: '#wrap .s_banner .row > :first-child',
    },
    removeSelectedBlock(),
    {
        content: "Check that #wrap is empty",
        trigger: '#wrap:empty',
        run: () => null,
    },
]);
});
