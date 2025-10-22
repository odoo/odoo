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
        url: "/",
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
            trigger: ":iframe .s_tabs .s_tabs_content",
            run() {
                if (this.anchor.querySelectorAll(".tab-pane").length !== 2) {
                    console.error("There should be exactly 2 tab panes in the DOM.");
                }
            },
        },
        {
            content: "Check that the first tab link is active",
            trigger: ":iframe .s_tabs .nav-item:nth-of-type(1) .nav-link.active",
        },
        changeOption("Tabs", "button[aria-label='Add Tab']"),
        {
            content: "Check there are 3 tab panes",
            trigger: ":iframe .s_tabs .s_tabs_content",
            run() {
                if (this.anchor.querySelectorAll(".tab-pane").length !== 3) {
                    console.error("There should be exactly 3 tab panes in the DOM.");
                }
            },
        },
    ]
);
