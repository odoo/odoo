odoo.define('website.tour.carousel_content_removal', function (require) {
'use strict';

const tour = require('web_tour.tour');

tour.register("carousel_content_removal", {
    test: true,
    url: "/",
}, [{
    trigger: "a[data-action=edit]",
    content: "Click the Edit button.",
    extra_trigger: ".homepage",
}, {
    trigger: "#snippet_structure .oe_snippet:has(span:contains('Carousel')) .oe_snippet_thumbnail",
    content: "Drag the Carousel block and drop it in your page.",
    run: "drag_and_drop #wrap",
},
{
    trigger: ".carousel .carousel-item.active .carousel-content",
    content: "Select the active carousel item.",
}, {
    trigger: ".oe_overlay.oe_active .oe_snippet_remove",
    content: "Remove the active carousel item.",
},
{
    trigger: ".carousel .carousel-item.active .container:not(:has(*))",
    content: "Check for a carousel slide with an empty container tag",
    run: function () {},
}]);

});
