/** @odoo-module **/

import {
    changeOption,
    clickOnSnippet,
    insertSnippet,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

function removeSelectedBlock() {
    return {
        content: "Remove selected block",
        trigger: '#oe_snippets we-customizeblock-options:nth-last-child(3) .oe_snippet_remove',
        run: "click",
    };
}

registerWebsitePreviewTour('snippet_empty_parent_autoremove', {
    url: '/',
    edition: true,
}, () => [
    // Base case: remove both columns from text - image
    ...insertSnippet({
        id: 's_text_image',
        name: 'Text - Image',
        groupName: "Content",
    }),
    {
        content: "Click on second column",
        trigger: ':iframe #wrap .s_text_image .row > :nth-child(2)',
        run: "click",
    },
    removeSelectedBlock(),
    {
        content: "Click on first column",
        trigger: ':iframe #wrap .s_text_image .row > :first-child',
        run: "click",
    },
    removeSelectedBlock(),
    {
        content: "Check that #wrap is empty",
        trigger: ':iframe #wrap:empty',
    },

    // Cover: test that parallax, bg-filter and shape are not treated as content
    ...insertSnippet({
        id: 's_cover',
        name: 'Cover',
        groupName: "Intro",
    }),
    ...clickOnSnippet({
        id: 's_cover',
        name: 'Cover',
    }),
    // Add a shape
    changeOption('ColoredLevelBackground', 'Shape'),
    {
        content: "Check that the parallax element is present",
        trigger: ':iframe #wrap .s_cover .s_parallax_bg',
    },
    {
        content: "Check that the filter element is present",
        trigger: ':iframe #wrap .s_cover .o_we_bg_filter',
    },
    {
        content: "Check that the shape element is present",
        trigger: ':iframe #wrap .s_cover .o_we_shape',
    },
    // Add a column
    changeOption('layout_column', 'we-toggler'),
    changeOption('layout_column', '[data-select-count="1"]'),
    {
        content: "Click on the created column",
        trigger: ':iframe #wrap .s_cover .row > :first-child',
        run: "click",
    },
    removeSelectedBlock(),
    {
        content: "Check that #wrap is empty",
        trigger: ':iframe #wrap:empty',
    },
]);
