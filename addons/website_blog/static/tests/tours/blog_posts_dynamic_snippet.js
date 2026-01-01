import {
    changeOptionInPopover,
    clickOnSnippet,
    insertSnippet,
    registerWebsitePreviewTour,
    goBackToBlocks,
    changeOption,
} from "@website/js/tours/tour_utils";

const dynamicSnippet = {
    id: "s_dynamic_snippet",
    name: "Dynamic Snippet",
    groupName: "Debug",
};
const blogPostsSnippet = {
    id: "s_blog_posts_single_aside",
    name: "Blog Post",
    groupName: "Blogs",
};

registerWebsitePreviewTour(
    "blog_posts_dynamic_snippet_options",
    {
        url: "/?debug=1",
        edition: true,
    },
    () => [
        ...insertSnippet(blogPostsSnippet),
        ...clickOnSnippet({ ...blogPostsSnippet, id: "s_blog_posts" }),
        {
            content: "Check That the `Model` option is hidden",
            trigger: `.options-container:not(:has([data-label="Model"]))`,
        },
        {
            content: "Check That the `Template` option is hidden",
            trigger: `.options-container:not(:has([data-label="Template"]))`,
        },
        goBackToBlocks(),
        ...insertSnippet(dynamicSnippet),
        ...clickOnSnippet(dynamicSnippet),
        ...changeOptionInPopover("Dynamic Snippet", "Filter", "Latest Blog Posts"),
        ...changeOptionInPopover(
            "Dynamic Snippet",
            "Fetched Elements",
            `div[data-action-param*='1']`
        ),
        {
            content: "Check That the `Model` option is visible",
            trigger: `.options-container [data-label="Model"]`,
        },
        {
            content: "Check That the `Template` option is visible",
            trigger: `.options-container [data-label="Template"]`,
        },
        // Check that the content width classes resets when the template is changed.
        {
            content: "Set Full-Width on the snippet",
            ...changeOption("Dynamic Snippet", "[data-action-param='container-fluid']"),
        },
        ...changeOptionInPopover(
            "Dynamic Snippet",
            "Template",
            "[data-action-param*='blog_post_single_circle']"
        ),
        {
            content: "Check if the content width is not set as 'Full-width'",
            trigger: ":iframe .s_dynamic_snippet_container.o_container_small:not(.container-fluid)",
        },
    ]
);
