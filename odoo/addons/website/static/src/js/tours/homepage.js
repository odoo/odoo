/** @odoo-module **/

import wTourUtils from "@website/js/tours/tour_utils";

const snippets = [
    {
        id: 's_banner',
        name: 'Banner',
    },
    {
        id: 's_three_columns',
        name: 'Columns',
    },
    {
        id: 's_text_image',
        name: 'Image - Text',
    },
    {
        id: 's_masonry_block',
        name: 'Masonry',
    },
    {
        id: 's_title',
        name: 'Title',
    },
    {
        id: 's_showcase',
        name: 'Showcase',
    },
    {
        id: 's_call_to_action',
        name: 'Call to Action',
    },
    {
        id: 's_quotes_carousel',
        name: 'Quotes',
    },
];

wTourUtils.registerThemeHomepageTour('homepage', () => [
    wTourUtils.dragNDrop(snippets[0], 'top'),
    wTourUtils.clickOnText(snippets[0], 'h1'),
    wTourUtils.goBackToBlocks(),
    wTourUtils.dragNDrop(snippets[1]),
    wTourUtils.dragNDrop(snippets[2]),
    wTourUtils.clickOnSnippet(snippets[2], 'top'),
    wTourUtils.changeBackgroundColor(),
    wTourUtils.goBackToBlocks(),
    wTourUtils.dragNDrop(snippets[3]),
    wTourUtils.dragNDrop(snippets[4], 'top'),
    wTourUtils.dragNDrop(snippets[5]),
    wTourUtils.dragNDrop(snippets[6]),
    wTourUtils.dragNDrop(snippets[7]),
]);
