/** @odoo-module */

import {
    changeOptionInPopover,
    clickOnSave,
    clickOnSnippet,
    insertSnippet,
    registerWebsitePreviewTour,
    clickOnEditAndWaitEditMode,
} from "@website/js/tours/tour_utils";

const blogPostsSnippet = {
    id: "s_blog_posts_big_picture",
    name: "Blog Posts",
    groupName: "Blogs",
};

const isSnippetVisible = (empty = false) => [
    {
        content: `Check that a dynamic snippet is visible ${
            empty ? "in edit mode" : "with content"
        }`,
        trigger: `:iframe .s_dynamic_snippet_blog_posts:not(.o_dynamic_snippet_empty):not(.o_dynamic_empty):not(.s_dynamic_empty)${
            !empty ? " h3:contains('Post Test')" : ""
        }`,
    },
];

const isSnippetHidden = () => [
    {
        content: "Check that a dynamic snippet with no content is hidden",
        trigger:
            ":iframe .o_dynamic_snippet_empty:not(:visible), :iframe .o_dynamic_empty:not(:visible), :iframe .s_dynamic_empty:not(:visible)",
    },
    ...clickOnEditAndWaitEditMode(),
    // A dynamic snippet is always visible in edit mode.
    ...isSnippetVisible(true),
];

registerWebsitePreviewTour(
    "blog_posts_dynamic_snippet_edit",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...insertSnippet(blogPostsSnippet),
        ...clickOnSnippet({ ...blogPostsSnippet, id: "s_blog_posts" }),
        ...changeOptionInPopover("Blog Posts", "Blog", "aaa Blog Test"),
        {
            content: "Check that the blog filter is applied",
            trigger: `:iframe .s_dynamic_snippet_blog_posts:not([data-filter-by-blog-id="-1"])`,
        },
        // A dynamic snippet is always visible in edit mode.
        ...isSnippetVisible(true),
        ...clickOnSave(),
        ...isSnippetVisible(),
    ]
);

registerWebsitePreviewTour(
    "blog_posts_dynamic_snippet_visible",
    {
        url: "/",
    },
    isSnippetVisible
);

registerWebsitePreviewTour(
    "blog_posts_dynamic_snippet_empty",
    {
        url: "/",
    },
    isSnippetHidden
);

registerWebsitePreviewTour(
    "blog_posts_dynamic_snippet_misconfigured",
    {
        url: "/",
    },
    () => [
        ...isSnippetHidden(),
        {
            content: "Check that the snippet 'missing option' warning is visible",
            trigger: ":iframe .s_dynamic_snippet_blog_posts .missing_option_warning",
        },
    ]
);
