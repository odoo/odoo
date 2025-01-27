/** @odoo-module */

import {
    insertSnippet,
    clickOnSnippet,
    changeOption,
    clickOnSave,
    registerWebsitePreviewTour,
    goBackToBlocks,
} from '@website/js/tours/tour_utils';

const carouselInnerSelector = ":iframe .carousel-inner";

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
},
    goBackToBlocks(),
    ...insertSnippet({
        id: "s_quotes_carousel",
        name: "Blockquote",
        groupName: "People",
}), {
    trigger: ":iframe .s_quotes_carousel_wrapper .carousel-item.active .s_blockquote",
    content: "Select the blockquote.",
    run: "click",
}, {
    trigger: ":iframe .oe_overlay.oe_active .oe_snippet_remove",
    content: "Remove the blockquote from the carousel item.",
    run: "click",
}, {
    trigger: ":iframe .s_quotes_carousel_wrapper .carousel-item.active:not(:has(.s_blockquote))",
    content: "Check that the blockquote has been removed and the carousel item is empty.",
}]);

registerWebsitePreviewTour("snippet_carousel", {
    url: "/",
    edition: true,
}, () => [
    ...insertSnippet({id: "s_carousel", name: "Carousel", groupName: "Intro"}),
    ...clickOnSnippet(".carousel .carousel-item.active"),
    // Slide to the right.
    changeOption("CarouselItem", 'we-button[data-switch-to-slide="right"]'),
    {
        content: "Check if the second slide is active",
        trigger: `${carouselInnerSelector} > div.active:nth-child(2)`,
    },
    // Add a slide (with the "CarouselItem" option).
    changeOption("CarouselItem", "we-button[data-add-slide-item]"),
    {
        content: "Check if there are four slides and if the third one is active",
        trigger: `${carouselInnerSelector}:has(div:nth-child(4)) > div.active:nth-child(3)`,
    },
    // Remove a slide.
    changeOption("CarouselItem", "we-button[data-remove-slide]"),
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
    changeOption("Carousel", "we-button[data-add-slide]"),
    {
        content: "Check if there are four slides and if the second one is active",
        trigger: `${carouselInnerSelector}:has(div:nth-child(4)) > div.active:nth-child(2)`,
    }, {
        content: "Check if the slide indicator was correctly updated",
        trigger: "we-customizeblock-options span:contains(' (2/4)')",
    },
    // Check if we can still remove a slide.
    changeOption("CarouselItem", "we-button[data-remove-slide]"),
    {
        content: "Check if there are three slides and if the first one is active",
        trigger: `${carouselInnerSelector}:has(div:nth-child(3)) > div.active:nth-child(1)`,
    },
    // Slide to the left.
    changeOption("CarouselItem", 'we-button[data-switch-to-slide="left"]'),
    {
        content: "Check if the third slide is active",
        trigger: `${carouselInnerSelector} > div.active:nth-child(3)`,
    },
    // Reorder the slides and make it the second one.
    changeOption("GalleryElement", 'we-button[data-position="prev"]'),
    {
        content: "Check if the second slide is active",
        trigger: `${carouselInnerSelector} > div.active:nth-child(2)`,
    },
    ...clickOnSave(),
    // Check that saving always sets the first slide as active.
    {
        content: "Check that the first slide became the active one",
        trigger: `${carouselInnerSelector} > div.active:nth-child(1)`,
    },
]);
