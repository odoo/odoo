/** @odoo-module */

import * as wTourUtils from '@website/js/tours/tour_utils';

const snippets = [
    {
        id: 's_kickoff',
        name: 'Kickoff',
        groupName: "Intro",
    },
    {
        id: 's_title',
        name: 'Title',
        groupName: "Text",
    },
    {
        id: 's_company_team',
        name: 'Team',
        groupName: "People",
    },
    {
        id: 's_image_text_overlap',
        name: 'Image - Text Overlap',
        groupName: "Content",
    },
    {
        id: 's_features',
        name: 'Features',
        groupName: "Content",
    },
    {
        id: 's_call_to_action',
        name: 'Call to Action',
        groupName: "Content",
    },
];

wTourUtils.registerThemeHomepageTour("yes_tour", () => [
    wTourUtils.assertCssVariable('--color-palettes-name', '"yes-3"'),
    ...wTourUtils.insertSnippet(snippets[0]),
    ...wTourUtils.insertSnippet(snippets[1]),
    ...wTourUtils.clickOnText(snippets[1], 'h2'),
    wTourUtils.goBackToBlocks(),
    ...wTourUtils.insertSnippet(snippets[2]),
    ...wTourUtils.insertSnippet(snippets[3]),
    ...wTourUtils.insertSnippet(snippets[4]),
    ...wTourUtils.insertSnippet(snippets[5]),
]);
