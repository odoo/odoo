/** @odoo-module **/

import * as wTourUtils from "@website/js/tours/tour_utils";

const snippets = [
    {
        id: 's_cover',
        name: 'Cover',
        groupName: "Intro",
    },
    {
        id: 's_text_image',
        name: 'Text - Image',
        groupName: "Content",
    },
    {
        id: 's_numbers_grid',
        name: 'Numbers Grid',
        groupName: "Content",
    },
    {
        id: 's_mockup_image',
        name: 'Mockup Image',
        groupName: "Content",
    },
    {
        id: 's_comparisons',
        name: 'Comparisons',
        groupName: "Content",
    },
    {
        id: 's_references',
        name: 'References',
        groupName: "Content",
    },
];


wTourUtils.registerThemeHomepageTour("graphene_tour", () => [
    wTourUtils.assertCssVariable('--color-palettes-name', '"base-1"'),
    ...wTourUtils.insertSnippet(snippets[0]),
    ...wTourUtils.clickOnText(snippets[0], 'h1', 'top'),
    wTourUtils.goBackToBlocks('left'),

    ...wTourUtils.insertSnippet(snippets[1]),

    ...wTourUtils.insertSnippet(snippets[2]),
    ...wTourUtils.insertSnippet(snippets[3], 'top'),

    ...wTourUtils.insertSnippet(snippets[4], 'top'),
    ...wTourUtils.clickOnSnippet(snippets[4], 'top'),
    wTourUtils.changeBackgroundColor('left'),
    wTourUtils.selectColorPalette(),
]);
