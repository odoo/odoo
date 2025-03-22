/** @odoo-module */

import wTourUtils from 'website.tour_utils';

const carouselInnerSelector = "iframe .carousel-inner";

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
    trigger: "iframe .oe_overlay.oe_active .oe_snippet_remove",
    content: "Remove the active carousel item.",
},
{
    trigger: "iframe .carousel .carousel-item.active .container:not(:has(*))",
    content: "Check for a carousel slide with an empty container tag",
    run: function () {},
}]);

wTourUtils.registerWebsitePreviewTour("snippet_carousel", {
    test: true,
    url: "/",
    edition: true,
}, [
    wTourUtils.dragNDrop({id: "s_carousel", name: "Carousel"}),
    wTourUtils.clickOnSnippet(".carousel .carousel-item.active"),
    // Slide to the right.
    wTourUtils.changeOption("CarouselItem", 'we-button[data-switch-to-slide="right"]'),
    {
        content: "Check if the second slide is active",
        trigger: `${carouselInnerSelector} > div.active:nth-child(2)`,
        run: () => {}, // This is a check.
    },
    // Add a slide (with the "CarouselItem" option).
    wTourUtils.changeOption("CarouselItem", "we-button[data-add-slide-item]"),
    {
        content: "Check if there are four slides and if the third one is active",
        trigger: `${carouselInnerSelector}:has(div:nth-child(4)) > div.active:nth-child(3)`,
        run: () => {}, // This is a check.
    },
     // Remove a slide.
     wTourUtils.changeOption("CarouselItem", "we-button[data-remove-slide]"),
    {
        content: "Check if there are three slides and if the second one is active",
        trigger: `${carouselInnerSelector}:has(div:nth-child(3)) > div.active:nth-child(2)`,
        run: () => {}, // This is a check.
    }, {
        trigger: "iframe .carousel .carousel-control-prev",
        content: "Slide the carousel to the left with the arrows.",
    }, {
        content: "Check if the first slide is active",
        trigger: `${carouselInnerSelector} > div.active:nth-child(1)`,
        run: () => {}, // This is a check.
    },
    // Add a slide (with the "Carousel" option).
    wTourUtils.changeOption("Carousel", "we-button[data-add-slide]"),
    {
        content: "Check if there are four slides and if the second one is active",
        trigger: `${carouselInnerSelector}:has(div:nth-child(4)) > div.active:nth-child(2)`,
        run: () => {}, // This is a check.
    }, {
        content: "Check if the slide indicator was correctly updated",
        trigger: "we-customizeblock-options span:contains(' (2/4)')",
        run: () => {},
    },
    // Check if we can still remove a slide.
    wTourUtils.changeOption("CarouselItem", "we-button[data-remove-slide]"),
    {
        content: "Check if there are three slides and if the first one is active",
        trigger: `${carouselInnerSelector}:has(div:nth-child(3)) > div.active:nth-child(1)`,
        run: () => {}, // This is a check.
    },
    // Slide to the left.
    wTourUtils.changeOption("CarouselItem", 'we-button[data-switch-to-slide="left"]'),
    {
        content: "Check if the third slide is active",
        trigger: `${carouselInnerSelector} > div.active:nth-child(3)`,
        run: () => {}, // This is a check.
    },
    ...wTourUtils.clickOnSave(),
    // Check that saving always sets the first slide as active.
    {
        content: "Check that the first slide became the active one",
        trigger: `${carouselInnerSelector} > div.active:nth-child(1)`,
        run: () => {}, // This is a check.
    },
]);
