import {
    changeOptionInPopover,
    insertSnippet,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

function goToSlide(slideIdx) {
    return [
        {
            content: `Click on slide #${slideIdx}`,
            trigger: `:iframe .carousel-indicators > button:nth-child(${slideIdx})`,
            run: "click",
        },
        {
            content: "Check that the right slide is active",
            trigger: `:iframe .s_carousel_multiple_item:nth-child(${slideIdx}).active`,
        },
        {
            content: "Check that we slid to that slide",
            trigger: `:iframe .carousel-indicators > button:nth-child(${slideIdx}).active`,
        },
    ];
}

registerWebsitePreviewTour(
    "snippet_carousel_multiple",
    {
        edition: true,
    },
    () => [
        ...insertSnippet({
            id: "s_carousel_multiple",
            name: "Carousel Multiple",
            groupName: "Intro",
        }),
        {
            content: "Click on the carousel",
            trigger: ":iframe .s_carousel_multiple",
            run: "click",
        },
        ...changeOptionInPopover(
            "Carousel Multiple",
            "Displayed slides",
            ".o-dropdown-item[data-class-action='o_displayed_items_1']"
        ),
        ...goToSlide(6),
        {
            content: "Slide to the next slide",
            trigger: ":iframe .carousel-control-next",
            run: "click",
        },
        // Since we display 1 slide, clicking "next" from slide 1 should loop
        // to the first slide
        {
            content: "Check that we slid to the 1st slide",
            trigger: ":iframe .carousel-indicators > button:nth-child(1).active",
        },
        {
            content: "Click on the first card",
            trigger: ":iframe .s_carousel_multiple_item:first-child",
            run: "click",
        },
        {
            content: "Check that the option container title is correct",
            trigger: ".options-container[data-container-title='Slide (1/6)']",
        },
        {
            content: "Go to the next carousel card",
            trigger: ".options-container .btn[title='Move Forward']",
            run: "click",
        },
        {
            content: "Check that the title updated",
            trigger: ".options-container[data-container-title='Slide (2/6)']",
        },
        // Adding a card with "+" should clone the current target.
        {
            content: "Add a new card with the '+' option header button",
            trigger: ".options-container .btn[title='Add Slide']:not(.o-hb-btn)",
            run: "click",
        },
        {
            content: "Check that there are 2 cards with #2 title now",
            trigger: ":iframe .s_carousel_multiple_item .card-title:contains('#2'):count(2)",
        },
        {
            content: "Check that there are 7 cards now",
            trigger: ":iframe .s_carousel_multiple_item:count(7)",
        },
        // Adding a card with the "Add slide" option should clone the first card.
        {
            content: "Unfold the carousel multiple options",
            trigger: ".options-container[data-container-title='Carousel Multiple']",
            run: "click",
        },
        {
            content: "Add a new card with the '+' option header button",
            trigger: ".hb-row .o-hb-btn[title='Add Slide']",
            run: "click",
        },
        {
            content: "Check that there are 2 cards with #1 title now",
            trigger: ":iframe .s_carousel_multiple_item .card-title:contains('#1'):count(2)",
        },
        {
            content: "Check that the new card is activated",
            trigger: ".options-container[data-container-title='Slide (2/8)']",
        },
        {
            content: "Check that there are 8 cards now",
            trigger: ":iframe .s_carousel_multiple_item:count(8)",
        },
        ...goToSlide(5),
        {
            content: "Click on the fifth card",
            trigger: ":iframe .s_carousel_multiple_item:nth-child(5)",
            run: "click",
        },
        {
            content: "Check that the correct card is activated",
            trigger: ".options-container[data-container-title='Slide (5/8)']",
        },
        {
            content: "Remove a card",
            trigger: ".options-container .btn[title='Remove Slide']",
            run: "click",
        },
        {
            content: "Check that there are no #3 cards",
            trigger: ":iframe .s_carousel_multiple:not(:has(.card-title:contains('#3')))",
        },
        {
            content: "Check that there are 7 cards now",
            trigger: ":iframe .s_carousel_multiple_item:count(7)",
        },
        {
            content: "Switch to mobile mode",
            trigger: ".o-snippets-top-actions .o-hb-btn[title='Mobile Preview']",
            run: "click",
        },
    ]
);
