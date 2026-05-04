import { registry } from "@web/core/registry";
import {
    changeOptionInPopover,
    clickOnSave,
    clickOnSnippet,
    insertSnippet,
    waitForEditMode,
} from "@website/js/tours/tour_utils";

registry.category("web_tour.tours").add("website_event_floating_snippets", {
    steps: () => [
        waitForEditMode,
        ...insertSnippet({
            id: "s_popup",
            name: "Popup",
            groupName: "Content",
        }),
        ...clickOnSnippet(".s_popup, .s_popup:not(:visible)"),
        ...changeOptionInPopover("Popup", "Show on", "All events"),
        ...clickOnSave(),
        {
            content: "Go to the event page.",
            trigger: ":iframe a[href='/event']",
            run: "click",
        },
        {
            content: "Open another event page.",
            trigger: ':iframe a:contains("Event B")',
            run: "click",
        },
        {
            content: "Check that we navigated to another page.",
            trigger: ':iframe h1:contains("Event B")',
        },
        {
            content: "Check that the popup is present on the other event page.",
            trigger: ":iframe .s_popup[data-show-on='allEvents']:not(:visible)",
        },
    ],
});
