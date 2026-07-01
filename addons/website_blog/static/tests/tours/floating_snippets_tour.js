import { registry } from "@web/core/registry";
import {
    changeOptionInPopover,
    clickOnSave,
    clickOnSnippet,
    insertSnippet,
    waitForEditMode,
} from "@website/js/tours/tour_utils";

registry.category("web_tour.tours").add("website_blog_floating_snippets", {
    steps: () => [
        waitForEditMode,
        ...insertSnippet({
            id: "s_popup",
            name: "Popup",
            groupName: "Content",
        }),
        ...clickOnSnippet(".s_popup, .s_popup:not(:visible)"),
        ...changeOptionInPopover("Popup", "Show on", "All blog posts"),
        ...clickOnSave(),
        {
            content: "Go to Blog B page.",
            trigger: ':iframe a:contains("Floating Snippets Blog B")',
            run: "click",
        },
        {
            content: "Check that we navigated to Blog B page.",
            trigger: ':iframe h1:contains("Floating Snippets Blog B")',
        },
        {
            content: "Check that the popup is present on the other blog page.",
            trigger: ":iframe .s_popup[data-show-on='allBlogPosts']:not(:visible)",
        },
    ],
});
