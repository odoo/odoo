odoo.define("website_blog.tour", function (require) {
    "use strict";

    var core = require("web.core");
    var tour = require("web_tour.tour");

    var _t = core._t;

    tour.register("blog", {
        url: "/",
    }, [{
        trigger: '#new-content-menu > a',
        content: _t("Click here to add new content to your website."),
        position: 'bottom',

    }, {
        trigger: "a[data-action=new_blog_post]",
        content: _t("Select this menu item to create a new blog post."),
        position: "bottom",
    }, {
        trigger: "button.btn-continue",
        extra_trigger: "form[id=\"editor_new_blog\"]",
        content: _t("Select the blog you want to add the post to."),
    }, {
        trigger: "div[data-oe-expression=\"blog_post.name\"]",
        extra_trigger: "#oe_snippets.o_loaded",
        content: _t("Write a title, the subtitle is optional."),
        position: "top",
        run: "text",
    }, {
        trigger: "we-button[data-background]:nth(1)",
        extra_trigger: "#wrap div[data-oe-expression=\"blog_post.name\"]:not(:containsExact(\"\"))",
        content: _t("Set a blog post <b>cover</b>."),
        position: "right",
    }, {
        trigger: ".o_select_media_dialog .o_we_search",
        content: _t("Search for an image. (eg: type \"business\")"),
        position: "top",
    }, {
        trigger: ".o_select_media_dialog .o_existing_attachment_cell:first img",
        extra_trigger: '.modal:has(.o_existing_attachment_cell:first)',
        content: _t("Choose an image from the library."),
        position: "top",
    }, {
        trigger: "#o_wblog_post_content",
        content: _t("<b>Write your story here.</b> Use the top toolbar to style your text: add an image or table, set bold or italic, etc. Drag and drop building blocks for more graphical blogs."),
        position: "top",
        run: function (actions) {
            actions.auto();
            actions.text("Blog content", this.$anchor.find("p"));
        },
    }, {
        trigger: "button[data-action=save]",
        extra_trigger: "#o_wblog_post_content .o_wblog_post_content_field p:first:not(:containsExact(" + _t("Start writing here...") + "))",
        content: _t("<b>Click on Save</b> to record your changes."),
        position: "bottom",
    }, {
        trigger: "a[data-action=show-mobile-preview]",
        extra_trigger: "body:not(.editor_enable)",
        content: _t("Use this icon to preview your blog post on <b>mobile devices</b>."),
        position: "bottom",
    }, {
        trigger: "button[data-dismiss=modal]",
        extra_trigger: '.modal:has(#mobile-viewport)',
        content: _t("Once you have reviewed the content on mobile, close the preview."),
        position: "right",
    }, {
        trigger: ".js_publish_management .js_publish_btn",
        extra_trigger: "body:not(.editor_enable)",
        position: "bottom",
        content: _t("<b>Publish your blog post</b> to make it visible to your visitors."),
    }, {
        trigger: "#customize-menu > a",
        extra_trigger: ".js_publish_management .js_publish_btn .css_unpublish:visible",
        content: _t("<b>That's it, your blog post is published!</b> Discover more features through the <i>Customize</i> menu."),
        position: "bottom",
        width: 500,
    }]);
});
