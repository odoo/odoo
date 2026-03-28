/** @odoo-module */

import * as wTourUtils from '@website/js/tours/tour_utils';

const snippets = [
    {
        id: 's_sidegrid',
        name: 'Side grid',
        groupName: "Intro",
    },
    {
        id: 's_numbers_list',
        name: 'Numbers list',
        groupName: "Content",
    },
    {
        id: 's_color_blocks_2',
        name: 'Big Boxes',
        groupName: "Content",
    },
    {
        id: 's_references',
        name: 'References',
        groupName: "People",
    },
    {
        id: 's_freegrid',
        name: 'Free grid',
        groupName: "Columns",
    },
];

wTourUtils.registerThemeHomepageTour("treehouse_tour", () => [
    wTourUtils.assertCssVariable('--color-palettes-name', '"default-28"'),
    ...wTourUtils.insertSnippet(snippets[0]),
    ...wTourUtils.clickOnText(snippets[0], 'h1', 'top'),
    wTourUtils.goBackToBlocks(),
    ...wTourUtils.insertSnippet(snippets[1]),
    ...wTourUtils.insertSnippet(snippets[2]),
    ...wTourUtils.insertSnippet(snippets[3]),
    ...wTourUtils.insertSnippet(snippets[4]),
    ...wTourUtils.clickOnSnippet(snippets[4], 'top'),
    wTourUtils.changeBackgroundColor(),
    wTourUtils.selectColorPalette(),
]);
