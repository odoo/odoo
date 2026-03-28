/** @odoo-module */

import * as wTourUtils from '@website/js/tours/tour_utils';
import { _t } from "@web/core/l10n/translation";

const snippets = [
    {
        id: 's_framed_intro',
        name: 'Framed Intro',
        groupName: "Intro",
    },
    {
        id: 's_image_text',
        name: 'Image Text',
        groupName: "Content",
    },
    {
        id: 's_three_columns',
        name: 'Three Columns',
        groupName: "Columns",
    },
    {
        id: 's_images_wall',
        name: 'Images Wall',
        groupName: "Images",
    },
    {
        id: 's_text_image',
        name: 'Text Image',
        groupName: "Content",
    },
    {
        id: 's_company_team_shapes',
        name: 'Team',
        groupName: "People",
    },
    {
        id: 's_title',
        name: 'Title',
        groupName: "Text",
    },
    {
        id: 's_call_to_action',
        name: 'Call to Action',
        groupName: "Content",
    },
];

wTourUtils.registerThemeHomepageTour("notes_tour", () => [
    wTourUtils.assertCssVariable('--color-palettes-name', '"default-19"'),
    ...wTourUtils.insertSnippet(snippets[0]),
    ...wTourUtils.clickOnText(snippets[0], 'h1'),
    wTourUtils.goBackToBlocks(),
    ...wTourUtils.insertSnippet(snippets[1]),
    ...wTourUtils.insertSnippet(snippets[2]),
    ...wTourUtils.clickOnSnippet(snippets[2]),
    wTourUtils.changeOption('Columns', 'setContainerWidth', _t('width')),
    wTourUtils.goBackToBlocks(),
    ...wTourUtils.insertSnippet(snippets[3]),
    ...wTourUtils.insertSnippet(snippets[4]),
    ...wTourUtils.insertSnippet(snippets[5]),
    ...wTourUtils.insertSnippet(snippets[6]),
    ...wTourUtils.insertSnippet(snippets[7]),
]);
