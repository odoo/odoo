/** @odoo-module */

import * as wTourUtils from '@website/js/tours/tour_utils';

const snippets = [
    {
        id: 's_intro_pill',
        name: 'Intro Pill',
        groupName: "Intro",
    },
    {
        id: 's_masonry_block_mosaic_template',
        name: 'Masonry',
        groupName: "Images",
    },
    {
        id: 's_pricelist_boxed',
        name: 'Pricelist Boxed',
        groupName: "Text",
    },
    {
        id: 's_features_wall',
        name: 'Features Wall',
        groupName: "Columns",
    },
    {
        id: 's_image_frame',
        name: 'Image Frame',
        groupName: "Images",
    },
    {
        id: 's_call_to_action',
        name: 'Call to Action',
        groupName: "Content",
    },
];

wTourUtils.registerThemeHomepageTour("beauty_tour", () => [
    wTourUtils.assertCssVariable('--color-palettes-name', '"default-light-3"'),
    ...wTourUtils.insertSnippet(snippets[0]),
    ...wTourUtils.clickOnText(snippets[0], 'h1'),
    wTourUtils.goBackToBlocks(),
    ...wTourUtils.insertSnippet(snippets[1]),
    ...wTourUtils.insertSnippet(snippets[2]),
    ...wTourUtils.insertSnippet(snippets[3]),
    ...wTourUtils.insertSnippet(snippets[4]),
    ...wTourUtils.insertSnippet(snippets[5]),
]);
