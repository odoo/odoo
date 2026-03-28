/** @odoo-module */

import * as wTourUtils from '@website/js/tours/tour_utils';

const snippets = [
    {
        id: 's_discovery',
        name: 'Discovery',
        groupName: "Intro",
    },
    {
        id: 's_key_images',
        name: 'Key Images',
        groupName: "Columns",
    },
    {
        id: 's_striped',
        name: 'Striped',
        groupName: "Content",
    },
    {
        id: 's_showcase',
        name: 'Showcase',
        groupName: "Content",
    },
    {
        id: 's_image_title',
        name: 'Image Title',
        groupName: "Images",
    },
    {
        id: 's_numbers_charts',
        name: 'Numbers Charts',
        groupName: "Content",
    },
    {
        id: 's_cta_card',
        name: 'CTA Card',
        groupName: "Content",
    },
];

wTourUtils.registerThemeHomepageTour("zap_tour", () => [
    wTourUtils.assertCssVariable('--color-palettes-name', '"base-2"'),
    ...wTourUtils.insertSnippet(snippets[0]),
    ...wTourUtils.clickOnText(snippets[0], 'h1', 'top'),
    wTourUtils.goBackToBlocks(),
    ...wTourUtils.insertSnippet(snippets[1]),
    ...wTourUtils.insertSnippet(snippets[2]),
    ...wTourUtils.insertSnippet(snippets[3]),
    ...wTourUtils.insertSnippet(snippets[4]),
    ...wTourUtils.insertSnippet(snippets[5]),
    ...wTourUtils.clickOnSnippet(snippets[5], 'top'),
    wTourUtils.changeBackgroundColor(),
    wTourUtils.selectColorPalette(),
    wTourUtils.goBackToBlocks(),
    ...wTourUtils.insertSnippet(snippets[6]),
]);
