import { registry } from "@web/core/registry";
import {
    changeOptionInPopover,
    clickOnSave,
    clickOnSnippet,
    insertSnippet,
    waitForEditMode,
} from "@website/js/tours/tour_utils";

registry.category("web_tour.tours").add("website_forum_floating_snippets", {
    steps: () => [
        waitForEditMode,
        ...insertSnippet({
            id: "s_popup",
            name: "Popup",
            groupName: "Content",
        }),
        ...clickOnSnippet(".s_popup, .s_popup:not(:visible)"),
        ...changeOptionInPopover("Popup", "Show on", "All Forums"),
        ...clickOnSave(),
        {
            content: "Go to the forums list page.",
            trigger: ":iframe a[href='/forum']",
            run: "click",
        },
        {
            content: "Open another forum page.",
            trigger: ':iframe a:contains("Floating Snippets Forum B")',
            run: "click",
        },
        {
            content: "Check that we navigated to another page.",
            trigger: ':iframe h1:contains("Floating Snippets Forum B")',
        },
        {
            content: "Check that the popup is present on the other forum page.",
            trigger: ":iframe .s_popup[data-show-on='allForums']:not(:visible)",
        },
    ],
});
