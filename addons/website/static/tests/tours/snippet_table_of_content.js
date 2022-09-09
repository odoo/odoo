/** @odoo-module */

import wTourUtils from 'website.tour_utils';

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
]);
