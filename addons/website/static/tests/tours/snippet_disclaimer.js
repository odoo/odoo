import {
    clickOnSnippet,
    changeOptionInPopover,
    registerWebsitePreviewTour,
    insertSnippet,
} from "@website/js/tours/tour_utils";

registerWebsitePreviewTour(
    "snippet_disclaimer",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...insertSnippet({id: "s_disclaimer", name: "Disclaimer"}),
        {
            content: "Check whether the Disclaimer snippet is dropped above navbar",
            trigger: ":iframe #o_snippet_above_header .s_disclaimer"
        },
        ...clickOnSnippet({ id: "s_disclaimer", name: "Disclaimer" }),
        ...changeOptionInPopover("Disclaimer", "Show On", "[data-action-value='currentPage']"),
        {
            content: "Check whether snippet moved to #wrap",
            trigger: ":iframe #wrap .s_disclaimer",
        },
    ]
);
