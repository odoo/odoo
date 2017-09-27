odoo.define("website_blog.tour", function (require) {
    "use strict";

    var core = require("web.core");
    var tour = require("web_tour.tour");
    var base = require("web_editor.base");

    var _t = core._t;

    tour.register("blog", {
        url: "/",
        wait_for: base.ready(),
    }, [tour.STEPS.WEBSITE_NEW_PAGE, {
        trigger: "a[data-action=new_blog_post]",
        content: _t("Select this menu item to create a new blog post."),
        position: "bottom",
    }, {
        trigger: "h1[data-oe-expression=\"blog_post.name\"]",
        extra_trigger: "body.editor_has_snippets",
        content: _t("Write a title, the subtitle is optional."),
        position: "top",
        run: "text",
    }, {
        trigger: "#oe_manipulators .oe_overlay.oe_active a.btn.btn-primary.btn-sm",
        extra_trigger: "#wrap h1[data-oe-expression=\"blog_post.name\"]:not(:containsExact(\"\"))",
        content: _t("Set a blog post <b>cover</b>."),
        position: "bottom",
    }, {
        trigger: "a:containsExact(" + _t("Change Cover")+ "):eq(1)",
        content: _t("Click here to change your post cover."),
        position: "right",
    }, {
        trigger: ".o_select_media_dialog .o_existing_attachment_cell:nth(1) img",
        extra_trigger: ".modal:has(.o_existing_attachment_cell:nth(1))",
        content: _t("Choose an image from the library."),
        position: "top",
    }, {
        trigger: ".o_select_media_dialog .btn.o_save_button",
        extra_trigger: ".o_existing_attachment_cell.o_selected",
        content: _t("Click on <b>Save</b> to set the picture as cover."),
        position: "top",
    }, {
        trigger: ".blog_content .s_text_block",
        content: _t("<b>Write your story here.</b> Use the top toolbar to style your text: add an image or table, set bold or italic, etc. Drag and drop building blocks for more graphical blogs."),
        position: "top",
        run: function (actions) {
            actions.auto();
            actions.text("Blog content", this.$anchor.find("p"));
        },
    }, {
        trigger: "button[data-action=save]",
        extra_trigger: "#blog_content section:first p:first:not(:containsExact(" + _t("Start writing here...") + "))",
        content: _t("<b>Click on Save</b> to record your changes."),
        position: "bottom",
    }, {
        trigger: "a[data-action=show-mobile-preview]",
        extra_trigger: "body:not(.editor_enable)",
        content: _t("Use this icon to preview your blog post on <b>mobile devices</b>."),
        position: "bottom",
    }, {
        trigger: "button[data-dismiss=modal]",
        extra_trigger: ".modal:has(#mobile-viewport)",
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
