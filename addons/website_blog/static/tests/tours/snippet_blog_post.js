import { registry } from "@web/core/registry";
import {
    changeOption,
    changeOptionInPopover,
    clickOnSnippet,
    insertSnippet,
    waitForEditMode,
} from "@website/js/tours/tour_utils";

registry.category("web_tour.tours").add("snippet_blog_bost", {
    steps: () => [
        waitForEditMode,
        // Check that the cover image option is only available when one blog post is displayed
        ...insertSnippet({
            id: "s_blog_posts_single_aside",
            name: "Blog Post",
            groupName: "Blogs",
        }),
        ...clickOnSnippet(".s_dynamic_snippet_blog_posts"),
        ...changeOptionInPopover("Blog Post", "Fetched Elements", "3"),
        {
            content: "Check if the cover image option is not visible",
            trigger: "[data-container-title='Blog Post']:not(:has([data-label='Cover Image']))",
        },
        ...changeOptionInPopover("Blog Post", "Fetched Elements", "1"),
        {
            content: "Check if the cover image option is visible",
            trigger: "[data-container-title='Blog Post'] [data-label='Cover Image']",
        },
        // Check that the content width classes resets when the template is changed.
        {
            content: "Set Full-Width on the snippet",
            ...changeOption("Blog Post", "[data-action-param='container-fluid']"),
        },
        ...changeOptionInPopover("Blog Post", "Template", "Circle"),
        {
            content: "Check if the content width is not set as 'Full-width'",
            trigger: ":iframe .s_dynamic_snippet_container.o_container_small:not(.container-fluid)",
        },
    ],
});
