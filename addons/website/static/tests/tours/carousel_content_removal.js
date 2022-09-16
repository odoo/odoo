/** @odoo-module */

import wTourUtils from 'website.tour_utils';

wTourUtils.registerWebsitePreviewTour("carousel_content_removal", {
    test: true,
    url: '/',
    edition: true,
}, [{
    trigger: "#snippet_structure .oe_snippet:has(span:contains('Carousel')) .oe_snippet_thumbnail",
    content: "Drag the Carousel block and drop it in your page.",
    run: "drag_and_drop iframe #wrap",
},
{
    trigger: "iframe .carousel .carousel-item.active .carousel-content",
    content: "Select the active carousel item.",
}, {
    trigger: ".oe_overlay.oe_active .oe_snippet_remove",
    content: "Remove the active carousel item.",
},
{
    trigger: "iframe .carousel .carousel-item.active .container:not(:has(*))",
    content: "Check for a carousel slide with an empty container tag",
    run: function () {},
}]);
