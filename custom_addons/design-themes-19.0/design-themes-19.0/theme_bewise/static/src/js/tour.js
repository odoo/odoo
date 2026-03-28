/** @odoo-module */
import * as wTourUtils from '@website/js/tours/tour_utils';

const snippets = [
    {
        id: 's_striped_center_top',
        name: 'Striped Center Top',
        groupName: "Intro",
    },
    {
        id: 's_title',
        name: 'Title',
        groupName: "Text",
    },
    {
        id: 's_color_blocks_2',
        name: 'Big Boxes',
        groupName: "Content",
    },
    {
        id: 's_faq_collapse',
        name: 'FAQ Block',
        groupName: "Text",
    },
    {
        id: 's_masonry_block_default_template',
        name: 'Masonry',
        groupName: "Images",
    },
    {
        id: 's_company_team_shapes',
        name: 'Team Shapes',
        groupName: "People",
    },
];

wTourUtils.registerThemeHomepageTour("bewise_tour", () => [
    wTourUtils.assertCssVariable('--color-palettes-name', '"default-19"'),
    ...wTourUtils.insertSnippet(snippets[0], 'top'),
    ...wTourUtils.clickOnText(snippets[0], 'h1', 'top'),
    wTourUtils.goBackToBlocks(),
    ...wTourUtils.insertSnippet(snippets[1], 'top'),
    ...wTourUtils.insertSnippet(snippets[2], 'top'),
    ...wTourUtils.insertSnippet(snippets[3], 'top'),
    ...wTourUtils.insertSnippet(snippets[4], 'top'),
    ...wTourUtils.insertSnippet(snippets[5], 'top'),
]);
