odoo.define("website_blog.tour", function (require) {
    "use strict";

    var core = require("web.core");
    var tour = require("web_tour.tour");

    var _t = core._t;

    tour.register("blog", {
        url: "/",
    }, [{
        trigger: "body:has(#o_new_content_menu_choices.o_hidden) #new-content-menu > a",
        content: _t("Click here to add new content to your website."),
        consumeVisibleOnly: true,
        position: 'bottom',
    }, {
        trigger: "a[data-action=new_blog_post]",
        content: _t("Select this menu item to create a new blog post."),
        position: "bottom",
    }, {
        trigger: "button.btn-continue",
        extra_trigger: "form[id=\"editor_new_blog\"]",
        content: _t("Select the blog you want to add the post to."),
        // Without demo data (and probably in most user cases) there is only
        // one blog so this step would not be needed and would block the tour.
        // We keep the step with "auto: true", so that the main python test
        // still works but never display this to the user anymore. We suppose
        // the user does not need guidance once that modal is opened. Note: if
        // you run the tour via your console without demo data, the tour will
        // thus fail as this will be considered.
        auto: true,
    }, {
        trigger: "div[data-oe-expression=\"blog_post.name\"]",
        extra_trigger: "#oe_snippets.o_loaded",
        content: _t("Write a title, the subtitle is optional."),
        position: "top",
        // FIXME instead of using the default 'click' event that is used to mark
        // DIV elements as consumed, we would like to use the 'input' event for
        // this specific contenteditable element. However, using 'input' here
        // makes the auto test not work as the 'text' run method stops working
        // correctly for contenteditable element whose 'consumeEvent' is set to
        // 'input'. The auto tests should be entirely independent of what is set
        // as 'consumeEvent'. While this is investigated and fixed, let's use
        // the 'mouseup' event. Indeed we cannot let it to 'click' because of
        // the old editor currently removing all click handlers on top level
        // editable content (which the blog post title area is).
        consumeEvent: 'mouseup',
        run: "text",
    }, {
        trigger: "we-button[data-background]:nth(1)",
        extra_trigger: "#wrap div[data-oe-expression=\"blog_post.name\"]:not(:containsExact(\"\"))",
        content: _t("Set a blog post <b>cover</b>."),
        position: "top",
    }, {
        trigger: ".o_select_media_dialog .o_we_search",
        content: _t("Search for an image. (eg: type \"business\")"),
        position: "top",
    }, {
        trigger: ".o_select_media_dialog .o_existing_attachment_cell:first img",
        alt_trigger: ".o_select_media_dialog .o_we_existing_attachments",
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
