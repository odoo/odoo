/** @odoo-module **/

import wTourUtils from "website.tour_utils";

/**
 * Makes sure that the avatar are visible when posting a comment.
 */
wTourUtils.registerWebsitePreviewTour("blog_avatar_comment", {
    test: true,
    url: "/blog",
}, [
    {
        content: "Click on the 'Post Test' blog",
        trigger: "iframe article a.o_blog_post_title:contains('Post Test')",
    },
    {
        content: "Check that we are on the correct blog post",
        trigger: "iframe [data-name='Blog Post Cover'] .o_wblog_post_title:contains('Post Test')",
        run: () => {}, // It is a check
    },
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    {
        content: "Click on the 'Customize' button",
        trigger: "#oe_snippets #snippets_menu .o_we_customize_snippet_btn",
    },
    {
        content: "Allow the comment on the blog",
        trigger: ".o_we_customize_panel we-button[data-customize-website-views='website_blog.opt_blog_post_comment']:not(.active)",
    },
    {
        content: "Ensure the comments are enabled on the blog",
        trigger: ".o_we_customize_panel we-button[data-customize-website-views='website_blog.opt_blog_post_comment'].active",
        run: () => {}, // It is a check
    },
    ...wTourUtils.clickOnSave(),
    {
        content: "Write a comment on the blog post",
        trigger: "iframe #o_wblog_post_comments .o_portal_chatter_composer_input textarea.form-control",
        run: "text A nice comment",
    },
    {
        content: "Click on 'Send'",
        trigger: "iframe #o_wblog_post_comments .o_portal_chatter_composer_input button[data-action='/mail/chatter_post']",
    },
    {
        content: "Check the image of the avatar",
        trigger: "iframe #o_wblog_post_comments .o_portal_chatter_message:contains('A nice comment') img.o_portal_chatter_avatar",
        run: () => {
            const imgEl = document.querySelector("iframe").contentDocument.querySelector("#o_wblog_post_comments .o_portal_chatter_message img.o_portal_chatter_avatar");
            fetch(imgEl.getAttribute("src")).then(function (answer) {
                // Check that the avatar is not displayed as the default
                // placeholder image.
                if (answer.headers.get("Content-Disposition").match(/mail_message-\d+-author_avatar/)) {
                    imgEl.dataset.showAvatar = "true";
                }
            });
        },
    },
    {
        content: "Check that the avatar is not the default placeholder",
        trigger: "iframe #o_wblog_post_comments .o_portal_chatter_message img.o_portal_chatter_avatar[data-show-avatar='true']",
        run: () => {}, // It is a check
    },
]
);
