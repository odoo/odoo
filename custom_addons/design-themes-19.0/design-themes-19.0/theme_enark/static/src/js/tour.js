/** @odoo-module **/

import * as wTourUtils from "@website/js/tours/tour_utils";

const snippets = [
    {
        id: 's_freegrid',
        name: 'Free grid',
        groupName: "Columns",
    },
    {
        id: 's_features_wall',
        name: 'Features Wall',
        groupName: "Columns",
    },
    {
        id: 's_numbers_list',
        name: 'Numbers list',
        groupName: "Content",
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
    {
        id: 's_cta_box',
        name: 'Box Call to Action',
        groupName: "Content",
    },
];

wTourUtils.registerThemeHomepageTour("enark_tour", () => [
    wTourUtils.assertCssVariable('--color-palettes-name', '"default-light-12"'),
    ...wTourUtils.insertSnippet(snippets[0]),
    ...wTourUtils.clickOnText(snippets[0], 'h1'),
    wTourUtils.goBackToBlocks(),
    ...wTourUtils.insertSnippet(snippets[1]),
    ...wTourUtils.insertSnippet(snippets[2]),
    ...wTourUtils.insertSnippet(snippets[3]),
    ...wTourUtils.insertSnippet(snippets[4]),
    ...wTourUtils.insertSnippet(snippets[5]),
    ...wTourUtils.insertSnippet(snippets[6]),
]);
