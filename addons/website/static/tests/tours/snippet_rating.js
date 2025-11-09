import {
    changeOptionInPopover,
    clickOnSnippet,
    insertSnippet,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

registerWebsitePreviewTour(
    "snippet_rating",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...insertSnippet({ id: "s_rating", name: "Rating" }),
        ...clickOnSnippet({ id: "s_rating", name: "Rating" }),
        ...changeOptionInPopover(
            "Rating",
            "Title Position",
            "[data-class-action='s_rating_inline']"
        ),
        {
            content: "Check whether s_rating_inline class applied or not",
            trigger: ":iframe .s_rating_inline",
        },
        ...changeOptionInPopover(
            "Rating",
            "Title Position",
            "[data-class-action='s_rating_no_title']"
        ),
        {
            content: "Check whether s_rating_no_title class applied or not",
            trigger: ":iframe .s_rating_no_title",
        },
        ...changeOptionInPopover("Rating", "Title Position", "Top"),
        {
            content: "Check whether s_rating_no_title class removed or not",
            trigger: ":iframe .s_rating:not(.s_rating_no_title)",
        },
    ]
);
