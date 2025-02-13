import { clickOnSave, registerWebsitePreviewTour } from "@website/js/tours/tour_utils";

/**
 * Makes sure that blog are only managable by Blog Manager Group.
 * It tests that whether a user with blog manager rights are able to create or
 * edit website blog or not.
 */
registerWebsitePreviewTour("blog_manager", {
    url: "/blog",
}, () => [{
        trigger: "body:not(:has(#o_new_content_menu_choices)) .o_new_content_container > a",
        content: "Click here to add new content to your website.",
        run: "click",
    }, {
        trigger: "a[data-module-xml-id='base.module_website_blog']",
        content: "Select this menu item to create a new blog post.",
        run: "click",
    }, {
        trigger: "div[name='name'] input",
        content: "Enter your post's title",
        run: "edit Manager Blog",
    }, {
        trigger: "button.o_form_button_save",
        content: "Select the blog you want to add the post to.",
        run: "click",
    },
    {
        trigger: ":iframe h1[data-oe-expression='blog_post.name']",
        content: "Edit your Blog title",
        run: "editor Manager Blog Test Title",
    },
    {
        trigger: ":iframe #o_wblog_post_content p",
        content: "Edit your Blog content.",
        run: "editor Manager Blog Test Content",
    },
    ...clickOnSave(),
    {
        trigger: ":iframe #o_wblog_post_content p:contains('Manager Blog Test Content')",
        content: "Check if blog get edited!",
    },
]);

/**
 * Makes sure that blog are only managable by Blog Manager Group.
 * It tests that whether a non manager user are able to create or edit
 * website blog or not.
 */
registerWebsitePreviewTour("blog_no_manager", {
    url: "/blog",
}, () => [{
        trigger: "body:not(:has(#o_new_content_menu_choices)) .o_new_content_container > a",
        content: "Click here to add new content to your website.",
        run: "click",
    }, {
        trigger: "#o_new_content_menu_choices:not(a:has([data-module-xml-id='base.module_website_blog']))",
        content: "Check if Blog 1t Option is Present or Not.",
    }, {
        trigger: "#o_new_content_menu_choices",
        content: "Close New Content Menu",
        run: "click",
    }, {
        trigger: ":iframe article[name='blog_post'] a:contains('Manager Blog')",
        content: "Go to the 'Manager Blog' blog",
        run: "click",
    },
    // From here this tour tries to delete the post from the backend side.
    {
        trigger: ".o_website_edit_in_backend a",
        content: "Open Post Form in Backend",
        run: "click",
    }, {
        trigger: ".o_action_manager button[data-tooltip='Actions']",
        content: "Click on gear Icon",
        run: "click",
    }, {
        trigger: ".o_popover:not(:has(i.fa-trash-o))",
        content: "Check if delete action is available or not",
    }
]);
