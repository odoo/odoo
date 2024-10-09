/** @odoo-module */

import { insertSnippet, registerWebsitePreviewTour } from '@website/js/tours/tour_utils';

registerWebsitePreviewTour("carousel_content_removal", {
    url: '/',
    edition: true,
}, () => [
    ...insertSnippet({
        id: 's_carousel',
        name: 'Carousel',
        groupName: "Intro",
}), {
    trigger: ":iframe .carousel .carousel-item.active .carousel-content",
    content: "Select the active carousel item.",
    run: "click",
}, {
    trigger: ":iframe .oe_overlay.oe_active .oe_snippet_remove",
    content: "Remove the active carousel item.",
    run: "click",
}, {
    trigger: ":iframe .carousel .carousel-item.active .container:not(:has(*)):not(:visible)",
    content: "Check for a carousel slide with an empty container tag",
}]);
