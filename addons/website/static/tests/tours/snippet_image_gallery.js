/** @odoo-module */

import wTourUtils from 'website.tour_utils';

wTourUtils.registerWebsitePreviewTour('snippet_image_gallery', {
    test: true,
    url: '/',
    edition: true,
}, [
    wTourUtils.dragNDrop({id: 's_image_gallery', name: 'Images Wall'}),
    ...wTourUtils.clickOnSave(),
    {
        content: 'Click on an image of the Image Wall',
        trigger: 'iframe .s_image_gallery img',
        run: 'click',
    },
    {
        content: 'Check that the modal has opened properly',
        trigger: 'iframe .s_gallery_lightbox img',
        run: () => {}, // This is a check.
    },
]);
