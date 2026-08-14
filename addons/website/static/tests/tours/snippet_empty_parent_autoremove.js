/** @odoo-module **/

import wTourUtils from "@website/js/tours/tour_utils";

function removeSelectedBlock() {
    return {
        content: "Remove selected block",
        // The customize panel is rebuilt asynchronously (behind the edition
        // mutex) after every selection change or removal, and the stale panel
        // of the previous selection has the same shape as the fresh one, so a
        // bare :nth-last-child(3) can match the stale panel while its editor
        // is being destroyed and the click is then silently swallowed. Every
        // use of this helper removes a "Column" block and the stale panel of
        // its parent snippet has no such block, so scope the match to it.
        trigger: '#oe_snippets we-customizeblock-options:nth-last-child(3):has(we-title:contains("Column")) .oe_snippet_remove',
    };
}

wTourUtils.registerWebsitePreviewTour('snippet_empty_parent_autoremove', {
    test: true,
    url: '/',
    edition: true,
}, () => [
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
        // The second column and its options panel are removed in the same
        // synchronous block of removeSnippet, so once the column has left the
        // iframe DOM the stale "Column" panel is guaranteed to be gone.
        content: "Wait for the second column to be removed",
        trigger: 'iframe #wrap .s_text_image .row > :first-child:last-child',
        isCheck: true,
    },
    {
        content: "Click on first column",
        trigger: 'iframe #wrap .s_text_image .row > :first-child',
    },
    removeSelectedBlock(),
    {
        content: "Check that #wrap is empty",
        trigger: 'iframe #wrap:empty',
    },

    // Cover: test that parallax, bg-filter and shape are not treated as content
    wTourUtils.dragNDrop({
        id: 's_cover',
        name: 'Cover',
    }),
    wTourUtils.clickOnSnippet({
        id: 's_cover',
        name: 'Cover',
    }),
    // Add a shape
    wTourUtils.changeOption('ColoredLevelBackground', 'Shape'),
    {
        content: "Check that the parallax element is present",
        trigger: 'iframe #wrap .s_cover .s_parallax_bg',
        run: () => null,
    },
    {
        content: "Check that the filter element is present",
        trigger: 'iframe #wrap .s_cover .o_we_bg_filter',
        run: () => null,
    },
    {
        content: "Check that the shape element is present",
        trigger: 'iframe #wrap .s_cover .o_we_shape',
        run: () => null,
    },
    // Add a column
    wTourUtils.changeOption('layout_column', 'we-toggler'),
    wTourUtils.changeOption('layout_column', '[data-select-count="1"]'),
    {
        content: "Click on the created column",
        trigger: 'iframe #wrap .s_cover .row > :first-child',
    },
    removeSelectedBlock(),
    {
        content: "Check that #wrap is empty",
        trigger: 'iframe #wrap:empty',
        run: () => null,
    },
]);
