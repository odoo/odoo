/** @odoo-module */

import * as wTourUtils from '@website/js/tours/tour_utils';
import { _t } from "@web/core/l10n/translation";

const snippets = [
    {
        id: 's_mockup_image',
        name: 'Mockup Image',
        groupName: "Content",
    },
    {
        id: 's_references',
        name: 'References',
        groupName: "People",
    },
    {
        id: 's_text_image',
        name: 'Image - Text',
        groupName: "Content",
    },
    {
        id: 's_text_image',
        name: 'Text - Image',
        groupName: "Content",
    },
    {
        id: 's_showcase',
        name: 'Showcase',
        groupName: "Content",
    },
    {
        id: 's_faq_collapse',
        name: 'FAQ Block',
        groupName: "Text",
    },
    {
        id: 's_cta_box',
        name: 'Box Call to Action',
        groupName: "Content",
    },
];

wTourUtils.registerThemeHomepageTour("odoo_experts_tour", () => [
    wTourUtils.assertCssVariable('--color-palettes-name', '"default-11"'),
    ...wTourUtils.insertSnippet(snippets[0]),
    ...wTourUtils.insertSnippet(snippets[1]),
    ...wTourUtils.insertSnippet(snippets[2]),
    ...wTourUtils.clickOnText(snippets[2], 'h2'),
    wTourUtils.goBackToBlocks(),
    ...wTourUtils.insertSnippet(snippets[3]),
    ...wTourUtils.insertSnippet(snippets[4]),
    ...wTourUtils.insertSnippet(snippets[5]),
    ...wTourUtils.clickOnSnippet(snippets[5], 'top'),
    wTourUtils.changeOption('FAQ Block', 'toggleBgShape', _t('Background Shape')),
    wTourUtils.clickOnElement("shape", ".builder_select_page [data-action-id='setBackgroundShape']"),
    wTourUtils.goBackToBlocks(),
    ...wTourUtils.insertSnippet(snippets[6]),
]);
