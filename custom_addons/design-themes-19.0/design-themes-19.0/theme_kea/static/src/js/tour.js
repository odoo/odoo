/** @odoo-module */

import * as wTourUtils from '@website/js/tours/tour_utils';

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
        id: 's_picture',
        name: 'Title - Image',
        groupName: "Images",
    },
    {
        id: 's_image_text',
        name: 'Image - Text',
        groupName: "Content",
    },
    {
        id: 's_color_blocks_2',
        name: 'Big Boxes',
        groupName: "Content",
    },
    {
        id: 's_media_list',
        name: 'Media List',
        groupName: "Content",
    },
];

wTourUtils.registerThemeHomepageTour("kea_tour", () => [
    wTourUtils.assertCssVariable('--color-palettes-name', '"bewise-2"'),
    ...wTourUtils.insertSnippet(snippets[0]),
    ...wTourUtils.clickOnText(snippets[0], 'h1'),
    wTourUtils.goBackToBlocks(),
    ...wTourUtils.insertSnippet(snippets[1]),
    ...wTourUtils.insertSnippet(snippets[2]),
    ...wTourUtils.insertSnippet(snippets[3]),
    ...wTourUtils.insertSnippet(snippets[4]),
    ...wTourUtils.insertSnippet(snippets[5]),
    ...wTourUtils.clickOnSnippet(snippets[5], 'top'),
    wTourUtils.changeBackgroundColor(),
    wTourUtils.selectColorPalette(),
]);
