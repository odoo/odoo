import {
    changeOptionInPopover,
    clickOnSnippet,
    insertSnippet,
    registerWebsitePreviewTour,
    goBackToBlocks,
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
<<<<<<< ac72267fceb54706559ca27d618591f8b6060cd0
        undeterministicTour_doNotCopy: true, // Remove this key to make the tour failed. ( It removes delay between steps )
||||||| 5a4eb9bfa243e71452326fc4301482591f74d2a2
        undeterministicTour_doNotCopy: true, // Remove this key to make the tour failed. ( It removes delay between steps )
        url: "/?debug=1",
=======
        url: "/",
>>>>>>> bd30acf7b8d64e2d8a818d5bde934d812026f32c
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
        {
            content: "Open Fetched Elements dropdown",
            trigger:
                "[data-container-title='Dynamic Snippet'] [data-label='Fetched Elements'] .o-hb-select-toggle",
            run: "click",
        },
        {
            content: "Set Fetched Elements to 1",
            trigger:
                ".o_popover .o-dropdown-item[data-action-id='numberOfRecords'][data-action-param='1']",
            run: "click",
        },
        {
            content: "Check That the `Model` option is visible",
            trigger: `.options-container [data-label="Model"]`,
        },
        {
            content: "Check That the `Template` option is visible",
            trigger: `.options-container [data-label="Template"]`,
        },
    ]
);
