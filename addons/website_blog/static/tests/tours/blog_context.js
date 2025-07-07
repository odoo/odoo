import {
    clickOnEditAndWaitEditMode,
    clickOnSnippet,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

registerWebsitePreviewTour(
    "blog_context_and_social_media",
    {
        url: "/blog",
    },
    () => [
        {
            content: "Ensure we are in blog page",
            trigger: ":iframe html[data-view-xmlid='website_blog.blog_post_short']",
        },
        {
            content: "Click on 'aaa Blog Test' Blog",
            trigger: ":iframe .website_blog nav .nav-item a:contains('aaa Blog Test')",
            run: "click",
        },
        {
            content: "Check that 'aaa Blog Test' Blog is open",
            trigger: ":iframe .website_blog nav .nav-item a.active:contains('aaa Blog Test')",
        },
        {
            content: "Click on New Post",
            trigger: ".o_menu_systray .o_new_content_container button",
            run: "click",
        },
        {
            content: "Click on Blog Post",
            trigger: ".o_new_content_menu_choices button[aria-label='Blog Post']",
            run: "click",
        },
        {
            content: "Check in dialog current Selected Blog is 'aaa Blog Test'",
            trigger: ".modal-dialog .o_field_widget[name='blog_id'] .o_input",
            run: function () {
                if (this.anchor.value !== "aaa Blog Test") {
                    console.error("Current selected blog should be 'aaa Blog Test'");
                }
            },
        },
        {
            content: "Click on Discard",
            trigger: ".modal-footer .o_form_button_cancel",
            run: "click",
        },
        ...clickOnEditAndWaitEditMode(),
        {
            content: "Check that SideBar is enabled",
            trigger: ":iframe #wrap #o_wblog_sidebar",
            run: "click",
        },
        ...clickOnSnippet("#o_wblog_sidebar .s_social_media"),
        {
            content: "Check Social Media Options are available",
            trigger: ".o_customize_tab table.o_social_media_list",
        },
        {
            content: "Click on Discard",
            trigger: ".o-snippets-top-actions [data-action='cancel']",
            run: "click",
        },
        {
            content: "Click on the first article",
            trigger: ":iframe article[name='blog_post'] a",
            run: "click",
        },
        {
            content: "Check the blog info is available",
            trigger: ":iframe #o_wblog_post_info",
        },
    ]
);
