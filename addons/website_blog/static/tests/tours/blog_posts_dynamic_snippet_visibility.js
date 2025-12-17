/** @odoo-module */

import {
    changeOption,
    clickOnSave,
    clickOnSnippet,
    insertSnippet,
    registerWebsitePreviewTour,
    clickOnEditAndWaitEditMode,
} from "@website/js/tours/tour_utils";

const blogPostsOptionName = "dynamic_snippet_blog_posts";
const blogPostsSnippet = {
    id: "s_blog_posts",
    name: "Blogs",
    groupName: "Blogs",
};

const isSnippetVisible = (empty = false) => [
    {
        content: `Check that a dynamic snippet is visible ${
            empty ? "in edit mode" : "with content"
        }`,
        trigger: `:iframe .s_dynamic_snippet_blog_posts:not(.o_dynamic_snippet_empty):not(.o_dynamic_empty):not(.s_dynamic_empty)${
            !empty ? " h5:contains('Post Test')" : ""
        }`,
    },
];

registerWebsitePreviewTour(
    "blog_posts_dynamic_snippet_edit",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...insertSnippet(blogPostsSnippet),
        ...clickOnSnippet(blogPostsSnippet),
        changeOption(
            blogPostsOptionName,
            `we-select[data-name="template_opt"] we-toggler`,
            "template"
        ),
        changeOption(
            blogPostsOptionName,
            `we-button[data-select-data-attribute="website_blog.dynamic_filter_template_blog_post_card"]`
        ),
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
    () => [
        {
            content: "Check that a dynamic snippet with no content is hidden",
            trigger:
                ":iframe .o_dynamic_snippet_empty:not(:visible), :iframe .o_dynamic_empty:not(:visible), :iframe .s_dynamic_empty:not(:visible)",
        },
        ...clickOnEditAndWaitEditMode(),
        // A dynamic snippet is always visible in edit mode.
        ...isSnippetVisible(true),
    ]
);
