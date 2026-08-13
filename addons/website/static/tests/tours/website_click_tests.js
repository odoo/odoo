/** @odoo-module **/

import {
    clickOnEditAndWaitEditMode,
    clickOnSave,
    clickOnSnippet,
    insertSnippet,
    goBackToBlocks,
    registerWebsitePreviewTour,
} from '@website/js/tours/tour_utils';
import { stepUtils } from "@web_tour/tour_service/tour_utils";

const cover = {
    id: 's_cover',
    name: 'Cover',
    groupName: "Intro",
};

registerWebsitePreviewTour('website_click_tour', {
    url: '/',
}, () => [
    stepUtils.waitIframeIsReady(),
    {
        content: "trigger a page navigation",
        trigger: ':iframe a[href="/contactus"]',
        run: "click",
    },
    {
        content: "wait for the page to be loaded",
        trigger: '.o_website_preview[data-view-xmlid="website.contactus"]',
    },
    ...clickOnEditAndWaitEditMode(),
    {
        content: "click on a link that would trigger navigation",
        trigger: ':iframe a[href="/"]',
        run: "click",
    },
    goBackToBlocks(),
    ...insertSnippet(cover),
    ...clickOnSnippet(cover),
    ...clickOnSave(),
]);
