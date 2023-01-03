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
]);
