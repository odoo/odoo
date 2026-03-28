/** @odoo-module */

import * as wTourUtils from '@website/js/tours/tour_utils';


const snippets = [
    {
        id: 's_kickoff',
        name: 'Kickoff',
        groupName: "Intro",
    },
    {
        id: 's_key_images',
        name: 'Key Images',
        groupName: "Columns",
    },
    {
        id: 's_process_steps',
        name: 'Steps',
        groupName: "Content",
    },
    {
        id: 's_freegrid',
        name: 'Free grid',
        groupName: "Columns",
    },
    {
        id: 's_image_text_overlap',
        name: 'Image - Text Overlap',
        groupName: "Content",
    },
    {
        id: 's_company_team_basic',
        name: 'Team Basic',
        groupName: "People",
    },
    {
        id: 's_title',
        name: 'Title',
        groupName: "Text",
    },
    {
        id: 's_images_wall',
        name: 'Images Wall',
        groupName: "Images",
    },
    {
        id: 's_references',
        name: 'References',
        groupName: "People",
    },
];

wTourUtils.registerThemeHomepageTour("orchid_tour", () => [
    wTourUtils.assertCssVariable('--color-palettes-name', '"default-light-9"'),
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
