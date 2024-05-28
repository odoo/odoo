/** @odoo-module */

import { isVisible } from '@odoo/hoot-dom';
import wTourUtils from '@website/js/tours/tour_utils';

const scrollToHeading = function (position) {
    return {
        content: `Scroll to h2 number ${position}`,
        trigger: `:iframe h2:eq(${position})`,
        run: function () {
            this.anchor.scrollIntoView(true);
        },
    };
};
const checkTOCNavBar = function (tocPosition, activeHeaderPosition) {
    return {
        content: `Check that the header ${activeHeaderPosition} is active for TOC ${tocPosition}`,
        trigger: `:iframe .s_table_of_content:eq(${tocPosition}) .table_of_content_link:eq(${activeHeaderPosition}).active `,
        run: () => {}, // This is a check.
    };
};

wTourUtils.registerWebsitePreviewTour('snippet_table_of_content', {
    test: true,
    url: '/',
    edition: true,
}, () => [
    wTourUtils.dragNDrop({id: 's_table_of_content', name: 'Table of Content'}),
    wTourUtils.dragNDrop({id: 's_table_of_content', name: 'Table of Content'}),
    // To make sure that the public widgets of the two previous ones started.
    wTourUtils.dragNDrop({id: 's_banner', name: 'Banner'}),
    ...wTourUtils.clickOnSave(),
    checkTOCNavBar(0, 0),
    checkTOCNavBar(1, 0),
    scrollToHeading(1),
    checkTOCNavBar(0, 1),
    checkTOCNavBar(1, 0),
    scrollToHeading(2),
    checkTOCNavBar(1, 0),
    scrollToHeading(3),
    checkTOCNavBar(1, 1),
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    {
        content: "Click on the first TOC's title",
        trigger: ':iframe .s_table_of_content:eq(0) h2',
        run: "click",
    },
    {
        content: "Hide the first TOC on mobile",
        trigger: '[data-toggle-device-visibility="no_mobile"]',
        run: "click",
    },
    // Go back to blocks tabs to avoid changing the first ToC options
    wTourUtils.goBackToBlocks(),
    {
        content: "Click on the second TOC's title",
        trigger: ':iframe .s_table_of_content:eq(1) h2',
        run: "click",
    },
    {
        content: "Hide the second TOC on desktop",
        trigger: '[data-toggle-device-visibility="no_desktop"]',
        run: "click",
    },
    ...wTourUtils.clickOnSave(),
    {
        content: "Check that we have the good TOC on desktop",
        trigger: ':iframe .s_table_of_content.o_snippet_mobile_invisible',
        run: () => {
            if (isVisible(':iframe .s_table_of_content.o_snippet_desktop_invisible')) {
                console.error('The mobile TOC should not be visible on desktop');
            }
        },
    },
    {
        content: "Toggle the mobile view",
        trigger: '.o_mobile_preview > a',
        run: "click",
    },
    {
        content: "Check that we have the good TOC on mobile",
        trigger: ':iframe .s_table_of_content.o_snippet_desktop_invisible',
        run: () => {
            if (isVisible(':iframe .s_table_of_content.o_snippet_mobile_invisible')) {
                console.error('The desktop TOC should not be visible on mobile');
            }
        },
    },
]);
