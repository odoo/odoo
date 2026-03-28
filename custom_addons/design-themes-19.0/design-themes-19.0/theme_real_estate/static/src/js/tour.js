/** @odoo-module **/

import * as wTourUtils from "@website/js/tours/tour_utils";

const snippets = [
    {
        id: 's_cover',
        name: 'Cover',
        groupName: "Intro",
    },
    {
        id: 's_image_text',
        name: 'Image - Text',
        groupName: "Content",
    },
    {
        id: 's_image_text',
        name: 'Image - Text',
        groupName: "Content",
    },
    {
        id: 's_three_columns',
        name: 'Columns',
        groupName: "Columns",
    },
    {
        id: 's_title',
        name: 'Title',
        groupName: "Text",
    },
    {
        id: 's_references',
        name: 'References',
        groupName: "People",
    },
    {
        id: 's_numbers_showcase',
        name: 'Numbers Showcase',
        groupName: "Content",
    },
    {
        id: 's_quotes_carousel',
        name: 'Quotes',
        groupName: "People",
    },
    {
        id: 's_call_to_action',
        name: 'Call To Action',
        groupName: "Content",
    },
];

wTourUtils.registerThemeHomepageTour("real_estate_tour", () => [
    wTourUtils.assertCssVariable('--color-palettes-name', '"default-28"'),
    ...wTourUtils.insertSnippet(snippets[0]),
    ...wTourUtils.clickOnText(snippets[0], 'h1'),
    wTourUtils.goBackToBlocks(),
    ...wTourUtils.insertSnippet(snippets[1]),
    ...wTourUtils.insertSnippet(snippets[2]),
    ...wTourUtils.insertSnippet(snippets[3]),
    ...wTourUtils.insertSnippet(snippets[4]),
    ...wTourUtils.clickOnSnippet(snippets[4]),
    wTourUtils.changeBackgroundColor(),
    wTourUtils.selectColorPalette(),
    wTourUtils.goBackToBlocks(),
    ...wTourUtils.insertSnippet(snippets[5]),
    ...wTourUtils.insertSnippet(snippets[6]),
    ...wTourUtils.insertSnippet(snippets[7]),
    ...wTourUtils.insertSnippet(snippets[8]),
]);
