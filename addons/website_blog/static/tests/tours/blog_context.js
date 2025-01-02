import {
    clickOnEditAndWaitEditMode,
    clickOnSave,
    clickOnSnippet,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

registerWebsitePreviewTour(
    "blog_context",
    {
        url: "/blog",
    },
    () => [
        {
            content: "Click on New Post",
            trigger: ".o_menu_systray_item.o_new_content_container a",
            run: "click",
        },
        {
            content: "Click on Blog Post",
            trigger: "#o_new_content_menu_choices a p:contains('Blog Post')",
            run: "click",
        },
        {
            content: "Check in dialog current Selected Blog is Astronomy",
            trigger: ".modal-dialog .o_field_widget[name='blog_id'] .o_input",
            run: function () {
                if (this.anchor.value !== "Astronomy") {
                    console.error("Current selected blog Should be Astronomy");
                }
            },
        },
        {
            content: "Click on Discard",
            trigger: ".modal-footer .o_form_button_cancel",
            run: "click",
        },
        {
            content: "Go back to blog page",
            trigger: "#o_new_content_menu_choices",
            run: "click",
        },
        {
            content: "Click on Travel Blog",
            trigger: ":iframe .website_blog nav .nav-item a:contains('Travel')",
            run: "click",
        },
        {
            content: "Check that Travel Blog is open",
            trigger: ":iframe .website_blog nav .nav-item a.active:contains('Travel')",
        },
        {
            content: "Click on New Post",
            trigger: ".o_menu_systray_item.o_new_content_container a",
            run: "click",
        },
        {
            content: "Click on Blog Post",
            trigger: "#o_new_content_menu_choices a p:contains('Blog Post')",
            run: "click",
        },
        {
            content: "Check in dialog current Selected Blog is Travel",
            trigger: ".modal-dialog .o_field_widget[name='blog_id'] .o_input",
            run: function () {
                if (this.anchor.value !== "Travel") {
                    console.error("Current selected blog Should be Travel");
                }
            },
        },
        {
            content: "Click on Discard",
            trigger: ".modal-footer .o_form_button_cancel",
            run: "click",
        },
    ]
);

registerWebsitePreviewTour(
    "blog_social_media",
    {
        url: "/blog",
        edition: "true",
    },
    () => [
        {
            content: "Click on Blog Page to open options",
            trigger: ":iframe #wrap #o_wblog_index_content",
            run: "click",
        },
        {
            content: "Enable Sidebar Option",
            trigger: "we-button[data-name='blog_posts_sidebar_opt'] we-checkbox",
            run: "click",
        },
        {
            content: "Check that SideBar is enabled",
            trigger: ":iframe #wrap #o_wblog_sidebar",
        },
        ...clickOnSnippet("#o_wblog_sidebar .s_social_media"),
        {
            content: "Check Social Media Options are available",
            trigger:
                "#oe_snippets .o_we_customize_panel we-customizeblock-options we-title span:contains('Social Media')",
        },
        ...clickOnSave(),
        {
            content: "Open a Blog Post",
            trigger: ":iframe article[name=blog_post] a",
            run: "click",
        },
        ...clickOnEditAndWaitEditMode(),
        {
            content: "Click on Blog Post to get options",
            trigger: ":iframe #wrap #o_wblog_post_main",
            run: "click",
        },
        {
            content: "Check Layout option is Title Inside Cover",
            trigger:
                "#oe_snippets .o_we_customize_panel we-select we-toggler:contains('Title Inside Cover')",
        },
        {
            content: "Check that Blog Post has Blog Information",
            trigger: ":iframe section#o_wblog_post_main #o_wblog_post_info",
        },
    ]
);
