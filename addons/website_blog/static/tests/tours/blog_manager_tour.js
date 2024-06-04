import {
    clickOnSave,
    registerWebsitePreviewTour,
    clickOnEditAndWaitEditMode,
} from "@website/js/tours/tour_utils";

/**
 * Makes sure that blog are only managable by Blog Manager Group.
 */
registerWebsitePreviewTour(
    "blog_manager",
    {
        url: "/blog",
    },
    () => [
        {
            content: "Open create content menu.",
            trigger: ".o_menu_systray .o_new_content_container button",
            run: "click",
        },
        {
            content: "Select option to create a new blog post.",
            trigger: "button[data-module-xml-id='base.module_website_blog']",
            run: "click",
        },
        {
            content: "Enter your post's title",
            trigger: "div[name='name'] input",
            run: "edit Manager Blog",
        },
        {
            content: "Click on save button to create the blog post.",
            trigger: "button.o_form_button_save",
            run: "click",
        },
        ...clickOnEditAndWaitEditMode(),
        {
            content: "Edit blog title",
            trigger: ":iframe [data-oe-expression='blog_post.name']",
            run: "editor Manager Blog Test Title",
        },
        {
            content: "Edit blog content.",
            trigger: ":iframe #o_wblog_post_content p",
            run: "editor Manager Blog Test Content",
        },
        ...clickOnSave(),
        {
            content: "Check if blog get edited!",
            trigger: ":iframe #o_wblog_post_content p:contains('Manager Blog Test Content')",
        },
    ]
);

registerWebsitePreviewTour(
    "blog_no_manager",
    {
        url: "/blog",
    },
    () => [
        {
            content: "Open create content menu.",
            trigger: ".o_menu_systray .o_new_content_container button",
            run: "click",
        },
        {
            content: "Check if Blog Option is not present.",
            trigger:
                ".o_new_content_menu_choices:not(:has([data-module-xml-id='base.module_website_blog']))",
        },
        {
            content: "Click on the first article",
            trigger: ":iframe article[name='blog_post'] a",
            run: "click",
        },
        {
            content: "Open Post Form in Backend",
            trigger: ".o_website_edit_in_backend a",
            run: "click",
        },
        {
            content: "Click on gear Icon",
            trigger: ".o_action_manager button[data-tooltip='Actions']",
            run: "click",
        },
        {
            content: "Check if delete action is available or not",
            trigger: ".o_popover:not(:has(i.fa-trash-o))",
        },
    ]
);
