/** @odoo-module */

import * as wTourUtils from '@website/js/tours/tour_utils';

const snippets = [
    {
        id: 's_banner',
        name: 'Banner',
        groupName: "Intro",
    },
    {
        id: 's_color_blocks_2',
        name: 'Big Boxes',
        groupName: "Content",
    },
    {
        id: 's_title',
        name: 'Title',
        groupName: "Text",
    },
    {
        id: 's_text_image',
        name: 'Text - Image',
        groupName: "Content",
    },
    {
        id: 's_image_text',
        name: 'Image - Text',
        groupName: "Content",
    },
    {
        id: 's_numbers_showcase',
        name: 'Numbers Showcase',
        groupName: "Content",
    },
    {
        id: 's_company_team',
        name: 'Team',
        groupName: "People",
    },
    {
        id: 's_accordion_image',
        name: 'Accordion Image',
        groupName: "Content",
    },
    {
        id: 's_cta_card',
        name: 'Card Call to Action',
        groupName: "Content",
    },
];

wTourUtils.registerThemeHomepageTour("clean_tour", () => [
    wTourUtils.assertCssVariable('--color-palettes-name', '"clean-1"'),
    ...wTourUtils.insertSnippet(snippets[0]),
    ...wTourUtils.clickOnText(snippets[0], 'h1'),
    wTourUtils.goBackToBlocks(),
    ...wTourUtils.insertSnippet(snippets[1]),
    ...wTourUtils.insertSnippet(snippets[2]),
    ...wTourUtils.insertSnippet(snippets[3]),
    ...wTourUtils.insertSnippet(snippets[4]),
    ...wTourUtils.insertSnippet(snippets[5]),
    ...wTourUtils.insertSnippet(snippets[6]),
    ...wTourUtils.insertSnippet(snippets[7]),
    ...wTourUtils.insertSnippet(snippets[8]),
]);
