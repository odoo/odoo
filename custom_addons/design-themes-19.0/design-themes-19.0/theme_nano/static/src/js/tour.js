/** @odoo-module */

import * as wTourUtils from '@website/js/tours/tour_utils';

const snippets = [
    {
        id: 's_discovery',
        name: 'Discovery',
        groupName: "Intro",
    },
    {
        id: 's_parallax',
        name: 'Parallax',
        groupName: "Images",
    },
    {
        id: 's_text_block',
        name: 'Text',
        groupName: "Text",
    },
    {
        id: 's_key_images',
        name: 'Key Images',
        groupName: "Columns",
    },
    {
        id: 's_image_text_overlap',
        name: 'Image - Text Overlap',
        groupName: "Content",
    },
    {
        id: 's_company_team',
        name: 'Team',
        groupName: "People",
    },
    {
        id: 's_references',
        name: 'References',
        groupName: "People",
    },
    {
        id: 's_numbers',
        name: 'Numbers',
        groupName: "Content",
    },
    {
        id: 's_cta_box',
        name: 'Box Call to Action',
        groupName: "Content",
    },
];

wTourUtils.registerThemeHomepageTour("nano_tour", () => [
    wTourUtils.assertCssVariable('--color-palettes-name', '"nano-1"'),
    ...wTourUtils.insertSnippet(snippets[0]),
    ...wTourUtils.clickOnText(snippets[0], 'h1', 'top'),
    wTourUtils.goBackToBlocks(),
    ...wTourUtils.insertSnippet(snippets[1]),
    ...wTourUtils.insertSnippet(snippets[2]),
    ...wTourUtils.clickOnSnippet(snippets[2], 'top'),
    wTourUtils.changeBackgroundColor(),
    wTourUtils.selectColorPalette(),
    wTourUtils.goBackToBlocks(),
    ...wTourUtils.insertSnippet(snippets[3]),
    ...wTourUtils.insertSnippet(snippets[4]),
    ...wTourUtils.insertSnippet(snippets[5]),
]);
