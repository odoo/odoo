odoo.define("website.tour.restricted_editor", function (require) {
"use strict";

var wTourUtils = require("website.tour_utils");

wTourUtils.registerWebsitePreviewTour("restricted_editor", {
    test: true,
    url: "/",
}, [
    ...wTourUtils.clickOnEditAndWaitEditMode(),
]);
});
