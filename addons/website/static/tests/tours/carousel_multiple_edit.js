import { insertSnippet, registerWebsitePreviewTour } from "@website/js/tours/tour_utils";

registerWebsitePreviewTour(
    "carousel_multiple_edit",
    {
        url: "/",
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
        {
            content: "Click on the dropdown menu to change the number of displayed slides",
            trigger: ".hb-row[data-label='Displayed slides'] .o-hb-select-toggle",
            run: "click",
        },
        {
            content: "Change number of displayed slides to 1",
            trigger: ".o-hb-select-dropdown-item[data-action-value='1']",
            run: "click",
        },
        {
            content: "Check that we are on the first slide",
            trigger: ":iframe .carousel-indicators > button:nth-child(1).active",
        },
        {
            content: "Click on the 4th slide",
            trigger: ":iframe .s_carousel_multiple_item:nth-child(4)",
            run: "click",
        },
        {
            content: "Check that it's active",
            trigger: ":iframe .s_carousel_multiple_item:nth-child(4).active",
        },
        {
            content: "Check that we slid to the 4th slide",
            trigger: ":iframe .carousel-indicators > button:nth-child(4).active",
        },
    ]
);
