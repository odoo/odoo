import {
    clickOnSave,
    clickOnEditAndWaitEditMode,
    changeOptionInPopover,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

registerWebsitePreviewTour(
    "blog_next_article",
    {
        url: "/blog",
    },
    () => [
        {
            content: "Open the blog 'Post Test 1'",
            trigger: ":iframe .o_wblog_post a:contains('Post Test 1')",
            run: "click",
        },
        ...clickOnEditAndWaitEditMode(),
        {
            content: "Click on the style tab.",
            trigger: "button[data-name='customize']",
            run: "click",
        },
        ...changeOptionInPopover("Blog Page", "Bottom", "Next Article"),
        ...clickOnSave(),
        {
            content: "Check if the next article is 'Post Test 3'",
            trigger:
                ":iframe .next-article .o_wblog_post_title .o_wblog_post_name:contains('Post Test 3')",
        },
        ...clickOnEditAndWaitEditMode(),
        ...changeOptionInPopover("Blog Page", "Bottom", "Recommended"),
        ...changeOptionInPopover("Blog Page", "Recommended Post", "New Post", true),
        ...clickOnSave(),
        {
            content: "Check if the recommended article is 'New Post'",
            trigger:
                ":iframe .next-article .o_wblog_post_title .o_wblog_post_name:contains('New Post')",
        },
    ]
);
