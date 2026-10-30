import {
    registerWebsitePreviewTour,
    insertSnippet,
    changeOption,
    clickOnSnippet,
} from "@website/js/tours/tour_utils";

registerWebsitePreviewTour(
    "snippet_tabs",
    {
        edition: true,
    },
    () => [
        ...insertSnippet({
            id: "s_tabs",
            name: "Tabs",
            groupName: "Content",
        }),
        ...clickOnSnippet(".s_tabs_common.s_tabs"),
        changeOption("Tabs", "button[aria-label='Remove Tab']"),
        {
            content: "Check that only 2 tab panes remain",
            trigger: ":iframe .s_tabs .s_tabs_content .tab-pane:count(2)",
        },
        {
            content: "Check that the first tab link is active",
            trigger: ":iframe .s_tabs .nav-item:nth-of-type(1) .nav-link.active",
        },
        {
            content: "Check that the last 2 tabs cannot be removed",
            trigger: "[data-container-title='Tabs'] button[aria-label='Remove Tab']:disabled",
        },
        changeOption("Tabs", "button[aria-label='Add Tab']"),
        {
            content: "Check there are 3 tab panes",
            trigger: ":iframe .s_tabs .s_tabs_content .tab-pane:count(3)",
        },
    ]
);
