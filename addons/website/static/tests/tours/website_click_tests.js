/** @odoo-module **/

import wTourUtils from '@website/js/tours/tour_utils';

const cover = {
    id: 's_cover',
    name: 'Cover',
};

wTourUtils.registerWebsitePreviewTour('website_click_tour', {
    test: true,
    url: '/',
}, () => [
    {
        content: "trigger a page navigation",
        trigger: 'iframe a[href="/contactus"]',
    },
    {
        content: "wait for the page to be loaded",
        trigger: '.o_website_preview[data-view-xmlid="website.contactus"]',
        run: () => null, // it's a check
    },
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    {
        content: "click on a link that would trigger navigation",
        trigger: 'iframe a[href="/"]',
    },
    wTourUtils.goBackToBlocks(),
    wTourUtils.dragNDrop(cover),
    wTourUtils.clickOnSnippet(cover),
    ...wTourUtils.clickOnSave(),
]);
