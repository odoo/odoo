/** @odoo-module */

import wTourUtils from '@website/js/tours/tour_utils';

wTourUtils.registerWebsitePreviewTour("carousel_content_removal", {
    test: true,
    url: '/',
    edition: true,
}, () => [
    wTourUtils.dragNDrop({
        id: 's_carousel',
        name: 'Carousel',
}), {
    trigger: "iframe .carousel .carousel-item.active .carousel-content",
    content: "Select the active carousel item.",
}, {
    trigger: "iframe .oe_overlay.oe_active .oe_snippet_remove",
    content: "Remove the active carousel item.",
}, {
    trigger: "iframe .carousel .carousel-item.active .container:not(:has(*))",
    content: "Check for a carousel slide with an empty container tag",
    allowInvisible: true,
    run: function () {},
}]);
