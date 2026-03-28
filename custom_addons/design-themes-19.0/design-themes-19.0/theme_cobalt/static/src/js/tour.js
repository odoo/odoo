/** @odoo-module */

import * as wTourUtils from '@website/js/tours/tour_utils';

const snippets = [
    {
        id: 's_banner',
        name: 'Banner',
        groupName: "Intro",
    },
    {
        id: 's_image_text',
        name: 'Image - Text',
        groupName: "Content",
    },
    {
        id: 's_key_images',
        name: 'Key Images',
        groupName: "Columns",
    },
    {
        id: 's_text_image',
        name: 'Text - Image',
        groupName: "Content",
    },
    {
        id: 's_company_team_detail',
        name: 'Team Detail',
        groupName: "People",
    },
    {
        id: 's_references_grid',
        name: 'References Grid',
        groupName: "People",
    },
];


wTourUtils.registerThemeHomepageTour("cobalt_tour", () => [
    wTourUtils.assertCssVariable('--color-palettes-name', '"default-8"'),
    ...wTourUtils.insertSnippet(snippets[0]),
    ...wTourUtils.clickOnText(snippets[0], 'h1', 'top'),
    wTourUtils.goBackToBlocks(),
    ...wTourUtils.insertSnippet(snippets[1]),
    ...wTourUtils.insertSnippet(snippets[2]),
    ...wTourUtils.insertSnippet(snippets[3]),
    ...wTourUtils.insertSnippet(snippets[4]),
    ...wTourUtils.insertSnippet(snippets[5]),
]);
