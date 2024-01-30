odoo.define('website.tour.specific_website_editor', function (require) {
'use strict';

const tour = require('web_tour.tour');
const wTourUtils = require("website.tour_utils");

wTourUtils.registerWebsitePreviewTour("generic_website_editor", {
    test: true,
    edition: true,
}, [{
    trigger: 'iframe body:not([data-hello="world"])',
    content: 'Check that the editor DOM matches its website-generic features',
    run: function () {}, // Simple check
}]);

// Good practice would have been to use `wTourUtils.registerWebsitePreviewTour`
// for this tour with `edition: true` and remove the first step to enter edit
// mode. Unfortunately this breaks the page and therefore the test fails for
// unknown reason.
tour.register('specific_website_editor', {
    test: true,
}, [
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    {
    trigger: 'iframe body[data-hello="world"]',
    content: 'Check that the editor DOM matches its website-specific features',
    run: function () {}, // Simple check
}]);
});
