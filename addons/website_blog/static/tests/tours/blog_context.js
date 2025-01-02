import {
    clickOnEditAndWaitEditMode,
    clickOnSave,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

registerWebsitePreviewTour("blog_context", {
    url: "/blog",
}, () => [
    {
        content: "Click on New Post",
        trigger: "div.o_menu_systray_item.o_new_content_container a",
        run: "click",
    },
    {
        content: "Click on Blog Post",
        trigger: "div#o_new_content_menu_choices a[title='Blog Post']",
        run: "click",
    },
    {
        content: "Check in dialog current Selected Blog is Astronomy",
        trigger: "div.modal-dialog main div[name='blog_id'] input",
        run: function() {
            if (this.anchor.value !== "Astronomy") {
                console.error("Current selected blog Should be Astronomy");
            }
        },
    },
    {
        content: "Click on Discard",
        trigger: "div.modal-dialog footer button.o_form_button_cancel",
        run: "click",
    },
    {
        content: "Go back to blog page",
        trigger: "div#o_new_content_menu_choices",
        run: "click",
    },
    {
        content: "Click on Travel Blog",
        trigger: ":iframe main div.website_blog nav ul li.nav-item a b:contains('Travel')",
        run: "click",
    },
    {
        content: "Check that Travel Blog is open",
        trigger: ":iframe main div.website_blog nav ul li.nav-item a.active b:contains('Travel')",
    },
    {
        content: "Click on New Post",
        trigger: "div.o_menu_systray_item.o_new_content_container a",
        run: "click",
    },
    {
        content: "Click on Blog Post",
        trigger: "div#o_new_content_menu_choices a[title='Blog Post']",
        run: "click",
    },
    {
        content: "Check in dialog current Selected Blog is Travel",
        trigger: "div.modal-dialog main div[name='blog_id'] input",
        run: function() {
            if (this.anchor.value !== "Travel") {
                console.error("Current selected blog Should be Travel");
            }
        },
    },
    {
        content: "Click on Discard",
        trigger: "div.modal-dialog footer button.o_form_button_cancel",
        run: "click",
    },
]);

registerWebsitePreviewTour('blog_social_media', {
    url: "/blog",
    edition: "true",
}, () => [
    {
        content: "Click on Blog Page to open options",
        trigger: ":iframe main div#wrap section#o_wblog_index_content",
        run: "click",
    },
    {
        content: "Enable Sidebar Option",
        trigger: "we-button[data-name='blog_posts_sidebar_opt'] we-checkbox",
        run: "click",
    },
    {
        content: "Check that SideBar is enabled",
        trigger: ":iframe main div#wrap section#o_wblog_index_content div#o_wblog_sidebar",
    },
    {
        content: "Click on Social Media",
        trigger: ":iframe main div#wrap div#o_wblog_sidebar div.s_social_media",
        run: "click",
    },
    {
        content: "Check Social Media Options are available",
        trigger: "div#oe_snippets div.o_we_customize_panel we-customizeblock-options we-title span:contains('Social Media')",
    },
    ...clickOnSave(),
    {
        content: "Open a Blog Post",
        trigger: ":iframe main section#o_wblog_index_content div#o_wblog_posts_loop div.row div article a",
        run: "click",
    },
    ...clickOnEditAndWaitEditMode(),
    {
        content: "Click on Blog Post to get options",
        trigger: ":iframe main div#wrap section#o_wblog_post_main",
        run: "click",
    },
    {
        content: "Check Layout option is Title Inside Cover",
        trigger: "div#oe_snippets div.o_we_customize_panel we-select we-toggler:contains('Title Inside Cover')",
    },
    {
        content: "Check that Blog Post has Blog Information",
        trigger: ":iframe main section#o_wblog_post_main div#o_wblog_post_info",
    },
    {
        content: "Enable Sidebar Option",
        trigger: "we-button[data-name='blog_post_sidebar_opt'] we-checkbox",
        run: "click",
    },
    {
        content: "Check that SideBar is enabled",
        trigger: ":iframe main div#wrap section#o_wblog_post_main div#o_wblog_post_sidebar",
    },
    {
        content: "Click on Social Media",
        trigger: ":iframe main div#wrap div#o_wblog_post_sidebar div.s_social_media",
        run: "click",
    },
    {
        content: "Check Social Media Options are available",
        trigger: "div#oe_snippets div.o_we_customize_panel we-customizeblock-options we-title span:contains('Social Media')",
    },
]);
