/** @odoo-module **/

import wTourUtils from '@website/js/tours/tour_utils';

wTourUtils.registerWebsitePreviewTour('website_multi_edition', {
    test: true,
    url: '/',
    edition: true,
}, () => [
    {
        content: 'Check the current page has not the elements that will be added',
        trigger: 'iframe body:not(:has(.s_text_image)):not(:has(.s_hr))',
        run: () => null,
    },
    // Edit the main element of the page
    wTourUtils.dragNDrop({
        id: 's_text_image',
        name: 'Text - Image',
    }),
    // Edit another part in the page, like the footer
    wTourUtils.dragNDrop({
        id: 's_hr',
        name: 'Separator',
    }),
    ...wTourUtils.clickOnSave(),
    {
        content: 'Check that the main element of the page was properly saved',
        trigger: 'iframe main .s_text_image',
        run: () => null,
    },
    {
        content: 'Check that the footer was properly saved',
        trigger: 'iframe footer .s_hr',
        run: () => null,
    },
]);
