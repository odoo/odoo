/** @odoo-module */

import * as wTourUtils from '@website/js/tours/tour_utils';

const snippets = [
    {
        id: 's_banner',
        name: 'Banner',
        groupName: "Intro",
    },
    {
        id: 's_discovery',
        name: 'Discovery',
        groupName: "Intro",
    },
    {
        id: 's_showcase',
        name: 'Showcase',
        groupName: "Content",
    },
    {
        id: 's_key_benefits',
        name: 'Key benefits',
        groupName: "Columns",
    },
    {
        id: 's_accordion_image',
        name: 'Accordion Image',
        groupName: "Content",
    },
    {
        id: 's_cta_box',
        name: 'Box Call to Action',
        groupName: "Content",
    },
];

wTourUtils.registerThemeHomepageTour("buzzy_tour", () => [
    wTourUtils.assertCssVariable('--color-palettes-name', '"default-24"'),
    ...wTourUtils.insertSnippet(snippets[0]),
    ...wTourUtils.clickOnText(snippets[0], 'h1', 'top'),
    wTourUtils.goBackToBlocks(),
    ...wTourUtils.insertSnippet(snippets[1]),
    ...wTourUtils.insertSnippet(snippets[2]),
    ...wTourUtils.insertSnippet(snippets[3]),
    ...wTourUtils.insertSnippet(snippets[4]),
    ...wTourUtils.insertSnippet(snippets[5]),
]);
