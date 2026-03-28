/** @odoo-module */
import * as wTourUtils from '@website/js/tours/tour_utils';
import { _t } from "@web/core/l10n/translation";

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
        id: 's_three_columns',
        name: 'Columns',
        groupName: "Columns",
    },
    {
        id: 's_product_list',
        name: 'Items',
        groupName: "Columns",
    },
    {
        id: 's_call_to_action',
        name: 'Call to Action',
        groupName: "Content",
    },
];

wTourUtils.registerThemeHomepageTour("kiddo_tour", () => [
    wTourUtils.assertCssVariable('--color-palettes-name', '"default-16"'),
    ...wTourUtils.insertSnippet(snippets[0]),
    ...wTourUtils.clickOnText(snippets[0], 'h1'),
    wTourUtils.goBackToBlocks(),
    ...wTourUtils.insertSnippet(snippets[1]),
    ...wTourUtils.insertSnippet(snippets[2]),
    ...wTourUtils.insertSnippet(snippets[3]),
    ...wTourUtils.clickOnSnippet(snippets[3]),
    wTourUtils.changeOption('Items', 'setContainerWidth', _t('width')),
    wTourUtils.goBackToBlocks(),
    ...wTourUtils.insertSnippet(snippets[4]),
]);
