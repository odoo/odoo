/** @odoo-module **/

import { click, waitFor } from "@odoo/hoot-dom";
import { browser } from "@web/core/browser/browser";
import wTourUtils from "@website/js/tours/tour_utils";

function removeSelectedBlock(selectedBlock) {
    return {
        content: "Remove selected block",
        trigger: `:iframe #wrap ${selectedBlock}`,
        async run(helpers) {
            const trashButton =
                "#oe_snippets we-customizeblock-options:nth-last-child(3) .oe_snippet_remove";
            // Select block
            click(helpers.anchor);
            await waitFor(trashButton, { timeout: 5000 });
            // click on trash
            await new Promise((resolve) => {
                browser.setTimeout(() => {
                    click(trashButton);
                    resolve();
                }, 1000);
            });
        },
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
    removeSelectedBlock('.s_text_image .row div:nth-child(2)'),
    removeSelectedBlock('.s_text_image .row div:nth-child(1)'),
    {
        content: "Check that #wrap is empty",
        trigger: ':iframe #wrap:empty',
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
    removeSelectedBlock('.s_cover .row:first-child'),
    {
        content: "Check that #wrap is empty",
        trigger: 'iframe #wrap:empty',
        run: () => null,
    },
]);
