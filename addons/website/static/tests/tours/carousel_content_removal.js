/** @odoo-module */

import wTourUtils from '@website/js/tours/tour_utils';

const carouselInnerSelector = ":iframe .carousel-inner";

wTourUtils.registerWebsitePreviewTour("carousel_content_removal", {
    test: true,
    url: '/',
    edition: true,
}, () => [
    ...wTourUtils.dragNDrop({
        id: 's_carousel',
        name: 'Carousel',
}), {
    trigger: ":iframe .carousel .carousel-item.active .carousel-content",
    content: "Select the active carousel item.",
    run: "click",
}, {
    trigger: ":iframe .oe_overlay.oe_active .oe_snippet_remove",
    content: "Remove the active carousel item.",
    run: "click",
}, {
    trigger: ":iframe .carousel .carousel-item.active .container:not(:has(*))",
    content: "Check for a carousel slide with an empty container tag",
    allowInvisible: true,
}]);

wTourUtils.registerWebsitePreviewTour("snippet_carousel", {
    test: true,
    url: "/",
    edition: true,
}, () => [
    ...wTourUtils.dragNDrop({id: "s_carousel", name: "Carousel"}),
    ...wTourUtils.clickOnSnippet(".carousel .carousel-item.active"),
    // Slide to the right.
    wTourUtils.changeOption("CarouselItem", 'we-button[data-switch-to-slide="right"]'),
    {
        content: "Check if the second slide is active",
        trigger: `${carouselInnerSelector} > div.active:nth-child(2)`,
    },
    // Add a slide (with the "CarouselItem" option).
    wTourUtils.changeOption("CarouselItem", "we-button[data-add-slide-item]"),
    {
        content: "Check if there are four slides and if the third one is active",
        trigger: `${carouselInnerSelector}:has(div:nth-child(4)) > div.active:nth-child(3)`,
    },
     // Remove a slide.
     wTourUtils.changeOption("CarouselItem", "we-button[data-remove-slide]"),
    {
        content: "Check if there are three slides and if the second one is active",
        trigger: `${carouselInnerSelector}:has(div:nth-child(3)) > div.active:nth-child(2)`,
    }, {
        trigger: ":iframe .carousel .carousel-control-prev",
        content: "Slide the carousel to the left with the arrows.",
        run: "click",
    }, {
        content: "Check if the first slide is active",
        trigger: `${carouselInnerSelector} > div.active:nth-child(1)`,
    },
    // Add a slide (with the "Carousel" option).
    wTourUtils.changeOption("Carousel", "we-button[data-add-slide]"),
    {
        content: "Check if there are four slides and if the second one is active",
        trigger: `${carouselInnerSelector}:has(div:nth-child(4)) > div.active:nth-child(2)`,
    }, {
        content: "Check if the slide indicator was correctly updated",
        trigger: "we-customizeblock-options span:contains(' (2/4)')",
    },
    // Check if we can still remove a slide.
    wTourUtils.changeOption("CarouselItem", "we-button[data-remove-slide]"),
    {
        content: "Check if there are three slides and if the first one is active",
        trigger: `${carouselInnerSelector}:has(div:nth-child(3)) > div.active:nth-child(1)`,
    },
    // Slide to the left.
    wTourUtils.changeOption("CarouselItem", 'we-button[data-switch-to-slide="left"]'),
    {
        content: "Check if the third slide is active",
        trigger: `${carouselInnerSelector} > div.active:nth-child(3)`,
    },
    // Reorder the slides and make it the second one.
    wTourUtils.changeOption("GalleryElement", 'we-button[data-position="prev"]'),
    {
        content: "Check if the second slide is active",
        trigger: `${carouselInnerSelector} > div.active:nth-child(2)`,
    },
    ...wTourUtils.clickOnSave(),
    // Check that saving always sets the first slide as active.
    {
        content: "Check that the first slide became the active one",
        trigger: `${carouselInnerSelector} > div.active:nth-child(1)`,
    },
]);
