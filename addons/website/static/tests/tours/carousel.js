/** @odoo-module */

import { delay } from "@odoo/hoot-dom";
import {
    insertSnippet,
    clickOnSnippet,
    changeOption,
    clickOnEditAndWaitEditMode,
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
    trigger: ".overlay .oe_snippet_remove",
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
    trigger: ".overlay .oe_snippet_remove",
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
        changeOption("Slide (1/3)", "[aria-label='Move Forward']"),
        checkSlides(3, 2),
        // Add a slide (with the "CarouselItem" option).
        changeOption("Slide (2/3)", "button[aria-label='Add Slide']"),
        checkSlides(4, 3),
        // Remove a slide.
        changeOption("Slide (3/4)", "button[aria-label='Remove Slide']"),
        checkSlides(3, 2),
        {
            trigger: ":iframe .carousel .carousel-control-prev",
            content: "Slide the carousel to the left with the arrows.",
            run: "click",
        },
        checkSlides(3, 1),
        // Add a slide (with the "Carousel" option).
        changeOption("Carousel", "[data-action-id='addSlide']"),
        checkSlides(4, 2),
        {
            content: "Check if the slide indicator was correctly updated",
            trigger: ".options-container span:contains(' (2/4)')",
        },
        // Check if we can still remove a slide.
        changeOption("Slide (2/4)", "button[aria-label='Remove Slide']"),
        checkSlides(3, 1),
        // Slide to the left.
        changeOption("Slide (1/3)", "[aria-label='Move Backward']"),
        checkSlides(3, 3),
        // Reorder the slides and make it the second one.
        changeOption("Slide (3/3)", "[data-action-value='prev']"),
        checkSlides(3, 2),
        ...clickOnSave(),
        // Check that saving always sets the first slide as active.
        checkSlides(3, 1),
    ]
);

registerWebsitePreviewTour("snippet_carousel_autoplay", {
    url: "/",
    edition: true,
}, () => [
    ...insertSnippet({id: "s_carousel", name: "Carousel", groupName: "Intro"}),
    ...clickOnSnippet(".carousel .carousel-item.active"),
    {
        content: "Decrease the interval between slides",
        trigger: "div[data-label='Speed'] input",
        run: 'edit 3',
    },
    {
        content: "Enable the autoplay option",
        trigger: "div[data-label='Autoplay'] input",
        run: 'click',
    },
    ...clickOnSave(),
    {
        content: "Check if the first slide is active and wait for 3s",
        trigger: `${carouselInnerSelector} > div.active:nth-child(1)`,
        run: () => new Promise(resolve => setTimeout(resolve, 3000)),
    },
    {
        content: "Check if the second slide is active",
        trigger: `${carouselInnerSelector} > div.active:nth-child(2)`,
    },
]);

const setSlideUrl = (urlText, matchText) => [
    {
        content: "Enter the URL to be linked with the slide",
        trigger: "div[data-action-id='setSlideAnchorUrl'] input[title='Your URL']",
        run: `edit ${urlText}`,
    },
    {
        content: "Select the URL from autocomplete dropdown",
        trigger: `ul.ui-autocomplete li div:contains('${matchText}')`,
        run: "click",
    },
];

const checkSlideNotClickable = () => ({
    content: "Check that the 'clickable-slide' class and anchor tag are removed",
    trigger: ":iframe .carousel-item.active:not(.clickable-slide):not(:has(a.slide-link))",
});

registerWebsitePreviewTour(
    "snippet_carousel_clickable_slides",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...insertSnippet({ id: "s_carousel", name: "Carousel", groupName: "Intro" }),
        ...clickOnSnippet(".carousel .carousel-item.active"),

        // Make the Slide clickable
        changeOption("Slide (1/3)", "[data-action-id='makeSlideClickable'] input"),

        {
            content: "Check that the 'clickable-slide' class is added to the carousel item",
            trigger: ":iframe .carousel-item.active.clickable-slide",
        },
        ...setSlideUrl("/contactus", "/contactus-thank-you"),
        {
            content: "Check that the anchor tag is added to the carousel item",
            trigger:
                ":iframe .carousel-item.active.clickable-slide a.slide-link[href='/contactus-thank-you']:not(:visible)",
        },

        // Enable the option to open the link in a new tab
        changeOption(
            "Slide (1/3)",
            "[data-label='Open in New Tab'] [data-attribute-action='target'] input"
        ),

        ...clickOnSave(),
        {
            content: "Check that the anchor tag is added to the carousel item",
            trigger:
                ":iframe .carousel-item.active.clickable-slide a.slide-link[href='/contactus-thank-you'][target='_blank']",
        },
        ...clickOnEditAndWaitEditMode(),
        ...clickOnSnippet(".carousel .carousel-item.active"),
        {
            content: "Check that the entered URL is correctly shown in the option and remove it",
            trigger: "div[data-action-id='setSlideAnchorUrl'] input:value(/contactus-thank-you)",
            run: "edit ",
        },
        {
            content: "Press Enter in the URL input",
            trigger: "div[data-action-id='setSlideAnchorUrl'] input",
            run: "press Enter",
        },
        {
            content: "Check that the anchor tag is removed",
            trigger: ":iframe .carousel-item.active.clickable-slide:not(:has(a.slide-link))",
        },
        {
            content: "Check that the 'Open in New Tab' option is no longer visible",
            trigger: "[data-label='Open in New Tab']:not(:visible)",
        },
        ...setSlideUrl("/contactus", "/contactus-thank-you"),

        // Turn off the 'Make Slide Clickable' option
        changeOption("Slide (1/3)", "[data-action-id='makeSlideClickable'] input"),

        checkSlideNotClickable(),

        // Make the slide clickable again
        changeOption("Slide (1/3)", "[data-action-id='makeSlideClickable'] input"),

        ...clickOnSave(),
        checkSlideNotClickable(),
    ]
);
