/** @odoo-module */

import wTourUtils from 'website.tour_utils';

const scrollToHeading = function (position) {
    return {
        content: `Scroll to h1 number ${position}`,
        trigger: `iframe h1:eq(${position})`,
        run: function () {
            this.$anchor[0].scrollIntoView(true);
        },
    };
};
const checkTOCNavBar = function (tocPosition, activeHeaderPosition) {
    return {
        content: `Check that the header ${activeHeaderPosition} is active for TOC ${tocPosition}`,
        trigger: `iframe .s_table_of_content:eq(${tocPosition}) .table_of_content_link:eq(${activeHeaderPosition}).active `,
        run: () => {}, // This is a check.
    };
};

wTourUtils.registerWebsitePreviewTour('snippet_table_of_content', {
    test: true,
    url: '/',
    edition: true,
}, [
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
    wTourUtils.clickOnEdit(),
    {
        content: "Click on the first TOC's title",
        trigger: 'iframe .s_table_of_content:eq(0) h1',
    },
    {
        content: "Hide the first TOC on mobile",
        trigger: '[data-toggle-device-visibility="no_mobile"]',
    },
    {
        content: "Click on the second TOC's title",
        trigger: 'iframe .s_table_of_content:eq(1) h1',
    },
    {
        content: "Hide the second TOC on desktop",
        trigger: '[data-toggle-device-visibility="no_desktop"]',
    },
    ...wTourUtils.clickOnSave(),
    {
        content: "Check that we have the good TOC on desktop",
        trigger: 'iframe .s_table_of_content.o_snippet_mobile_invisible',
        run: () => {
            if ($(document.querySelector('iframe .s_table_of_content.o_snippet_desktop_invisible'))
                    .is(':visible')) {
                console.error('The mobile TOC should not be visible on desktop');
            }
        },
    },
    {
        content: "Toggle the mobile view",
        trigger: '.o_mobile_preview',
    },
    {
        content: "Check that we have the good TOC on mobile",
        trigger: 'iframe .s_table_of_content.o_snippet_desktop_invisible',
        run: () => {
            if ($(document.querySelector('iframe .s_table_of_content.o_snippet_mobile_invisible'))
                    .is(':visible')) {
                console.error('The desktop TOC should not be visible on mobile');
            }
        },
    },
]);
