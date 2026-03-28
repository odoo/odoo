/** @odoo-module */
import * as wTourUtils from '@website/js/tours/tour_utils';

const snippets = [
    {
        id: 's_sidegrid',
        name: 'Sidegrid',
        groupName: "Intro",
    },
    {
        id: 's_features_wall',
        name: 'Features Wall',
        groupName: "Columns",
    },
    {
        id: 's_carousel',
        name: 'Carousel',
        groupName: "Intro",
    },
    {
        id: 's_timeline',
        name: 'Timeline',
        groupName: "Content",
    },
    {
        id: 's_quadrant',
        name: 'Quadrant',
        groupName: "Images",
    },
];

wTourUtils.registerThemeHomepageTour("avantgarde_tour", () => [
    wTourUtils.assertCssVariable('--color-palettes-name', '"default-15"'),
    ...wTourUtils.insertSnippet(snippets[0], 'top'),
    ...wTourUtils.clickOnText(snippets[0], 'h1', 'left'),
    wTourUtils.goBackToBlocks(),
    ...wTourUtils.insertSnippet(snippets[1], 'left'),
    ...wTourUtils.insertSnippet(snippets[2], 'top'),
    ...wTourUtils.insertSnippet(snippets[3], 'top'),
    ...wTourUtils.insertSnippet(snippets[4], 'top'),
]);
