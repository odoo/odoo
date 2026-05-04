import { registry } from "@web/core/registry";
import {
    changeOptionInPopover,
    clickOnSave,
    clickOnSnippet,
    insertSnippet,
    waitForEditMode,
} from "@website/js/tours/tour_utils";

registry.category("web_tour.tours").add("website_floating_snippets", {
    steps: () => [
        waitForEditMode,
        ...insertSnippet({
            id: "s_popup",
            name: "Popup",
            groupName: "Content",
        }),
        ...clickOnSnippet(".s_popup, .s_popup:not(:visible)"),
        ...changeOptionInPopover("Popup", "Show on", "All pages"),
        ...clickOnSave(),
        {
            content: "Go to Contact us page",
            trigger: ":iframe footer a[href='/contactus']",
            run: "click",
        },
        {
            content: "Check that we navigated to another page.",
            trigger: ":iframe #contactus_form",
        },
        {
            content: "Check that the popup is present on the other page.",
            trigger: ":iframe .s_popup[data-show-on='allPages']:not(:visible)",
        },
    ],
});
