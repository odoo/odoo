/** @odoo-module */

import { delay } from "@odoo/hoot-dom";
import {
    insertSnippet,
    clickOnSnippet,
    changeOption,
    clickOnSave,
    registerWebsitePreviewTour,
    goBackToBlocks,
} from "@website/js/tours/tour_utils";

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

const checkSlides = (number, position) => {
    const nSlide = (n) => `div.carousel-item:eq(${n})`;
    const hasNSlide = (n) => `:has(${nSlide(n - 1)}):not(:has(${nSlide(n)}))`;
    const activeSlide = (p) => `${nSlide(p - 1)}:is(.active)`;
    return {
        content: `Check if there are ${number} slides and if the ${position} is active`,
        trigger: `${carouselInnerSelector}${hasNSlide(number)} ${activeSlide(position)}`,
        async run() {
            // When continue the tour directly, slide menu can disappears or
            // action can not be done.
            await delay(500);
        },
    };
};

registerWebsitePreviewTour(
    "snippet_carousel",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...insertSnippet({ id: "s_carousel", name: "Carousel", groupName: "Intro" }),
        ...clickOnSnippet(".carousel .carousel-item.active"),
        // Slide to the right.
        changeOption("CarouselItem", 'we-button[data-switch-to-slide="right"]'),
        checkSlides(3, 2),
        // Add a slide (with the "CarouselItem" option).
        changeOption("CarouselItem", "we-button[data-add-slide-item]"),
        checkSlides(4, 3),
        // Remove a slide.
        changeOption("CarouselItem", "we-button[data-remove-slide]"),
        checkSlides(3, 2),
        {
            trigger: ":iframe .carousel .carousel-control-prev",
            content: "Slide the carousel to the left with the arrows.",
            run: "click",
        },
        checkSlides(3, 1),
        // Add a slide (with the "Carousel" option).
        changeOption("Carousel", "we-button[data-add-slide]"),
        checkSlides(4, 2),
        {
            content: "Check if the slide indicator was correctly updated",
            trigger: "we-customizeblock-options span:contains(' (2/4)')",
        },
        // Check if we can still remove a slide.
        changeOption("CarouselItem", "we-button[data-remove-slide]"),
        checkSlides(3, 1),
        // Slide to the left.
        changeOption("CarouselItem", 'we-button[data-switch-to-slide="left"]'),
        checkSlides(3, 3),
        // Reorder the slides and make it the second one.
        changeOption("GalleryElement", 'we-button[data-position="prev"]'),
        checkSlides(3, 2),
        // Ensure quickly adding/removing slides doesn’t give a traceback
        // (Includes delays to better simulate real user interactions and
        // expose potential race conditions.)
        {
            content: "Add a slide",
            trigger: ".snippet-option-CarouselItem .o_we_bg_success",
            async run(helpers) {
                helpers.click();
                await delay(360);
            },
        },
        {
            content: "Remove a slide",
            trigger: ".snippet-option-CarouselItem .o_we_bg_danger",
            async run(helpers) {
                helpers.click();
                await delay(360);
            },
        },
        {
            content: "Add a slide",
            trigger: ".snippet-option-CarouselItem .o_we_bg_success",
            async run(helpers) {
                helpers.click();
                await delay(360);
            },
        },
        ...clickOnSave(),
        // Check that saving always sets the first slide as active.
        checkSlides(4, 1),
    ]
);
