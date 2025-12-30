import {
    clickOnSnippet,
    changeOptionInPopover,
    registerWebsitePreviewTour,
    insertSnippet,
} from "@website/js/tours/tour_utils";

registerWebsitePreviewTour(
    "snippet_headline_tour",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...insertSnippet({ id: "s_headline", name: "Headline", groupName: "Contact & Forms" }),
        {
            content: "Check whether the Headline snippet is dropped above navbar",
            trigger: ":iframe #o_snippet_above_header .s_headline",
        },
        ...clickOnSnippet({ id: "s_headline", name: "Headline" }),
        ...changeOptionInPopover("Headline", "Show On", "[data-action-value='currentPage']"),
        {
            content: "Check whether snippet moved to #wrap",
            trigger: ":iframe #wrap .s_headline",
        },
    ]
);
