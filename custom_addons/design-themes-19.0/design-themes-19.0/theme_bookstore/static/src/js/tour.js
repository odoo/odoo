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
        id: 's_key_images',
        name: 'Key Images',
        groupName: "Columns",
    },
    {
        id: 's_title',
        name: 'Title',
        groupName: "Text",
    },
    {
        id: 's_accordion_image',
        name: 'Accordion Image',
        groupName: "Content",
    },
    {
        id: 's_cta_box',
        name: 'CTA Box',
        groupName: "Content",
    },
];

wTourUtils.registerThemeHomepageTour("bookstore_tour", () => [
    wTourUtils.assertCssVariable('--color-palettes-name', '"default-26"'),
    ...wTourUtils.insertSnippet(snippets[0]),
    ...wTourUtils.clickOnText(snippets[0], 'h1'),
    wTourUtils.goBackToBlocks(),
    ...wTourUtils.insertSnippet(snippets[1]),
    ...wTourUtils.insertSnippet(snippets[2]),
    ...wTourUtils.insertSnippet(snippets[3]),
    ...wTourUtils.insertSnippet(snippets[4]),
    ...wTourUtils.clickOnSnippet(snippets[4]),
    wTourUtils.changeOption('Box Call to Action', 'setContainerWidth', _t('width')),
    wTourUtils.goBackToBlocks(),
]);
