/** @odoo-module */

import * as wTourUtils from '@website/js/tours/tour_utils';

const snippets = [
    {
        id: 's_cover',
        name: 'Cover',
        groupName: "Intro",
    },
    {
        id: 's_references',
        name: 'References',
        groupName: "People",
    },
    {
        id: 's_image_text',
        name: 'Image - Text',
        groupName: "Content",
    },
    {
        id: 's_text_image',
        name: 'Text - Image',
        groupName: "Content",
    },
    {
        id: 's_masonry_block_images_template',
        name: 'Masonry',
        groupName: "Images",
    },
    {
        id: 's_faq_list',
        name: 'FAQ List',
        groupName: "Text",
    },
    {
        id: 's_cta_box',
        name: 'CTA Box',
        groupName: "Content",
    },
];


wTourUtils.registerThemeHomepageTour("paptic_tour", () => [
    wTourUtils.assertCssVariable('--color-palettes-name', '"base-2"'),
    ...wTourUtils.insertSnippet(snippets[0], 'top'),
    ...wTourUtils.clickOnText(snippets[0], 'h1', 'top'),
    wTourUtils.goBackToBlocks(),
    ...wTourUtils.insertSnippet(snippets[1], 'top'),
    ...wTourUtils.insertSnippet(snippets[2], 'top'),
    ...wTourUtils.insertSnippet(snippets[3], 'top'),
    ...wTourUtils.insertSnippet(snippets[4], 'top'),
    ...wTourUtils.insertSnippet(snippets[5], 'top'),
]);
