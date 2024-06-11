/** @odoo-module **/

import wTourUtils from "@website/js/tours/tour_utils";

wTourUtils.registerWebsitePreviewTour("restricted_editor", {
    test: true,
    url: "/",
}, () => [
    ...wTourUtils.clickOnEditAndWaitEditMode(),
]);
