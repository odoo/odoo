odoo.define("website_blog.tour", function (require) {
    "use strict";

    const {_t} = require("web.core");
    const {Markup} = require('web.utils');
    const wTourUtils = require('website.tour_utils');

    wTourUtils.registerEditionTour("blog", {
        url: "/",
    }, [{
        trigger: "body:not(:has(#o_new_content_menu_choices)) .o_new_content_container > a",
        content: _t("Click here to add new content to your website."),
        consumeVisibleOnly: true,
        position: 'bottom',
    }, {
        trigger: 'a[data-module-xml-id="base.module_website_blog"]',
        content: _t("Select this menu item to create a new blog post."),
        position: "bottom",
    }, {
        trigger: 'div[name="name"] input',
        content: _t("Enter your post's title"),
        position: "bottom",
    }, {
        trigger: "button.o_form_button_save",
        extra_trigger: 'div.o_field_widget[name="blog_id"]',
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
        trigger: "iframe h1[data-oe-expression=\"blog_post.name\"]",
        extra_trigger: "#oe_snippets.o_loaded",
        content: _t("Edit your title, the subtitle is optional."),
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
        extra_trigger: "iframe #wrap h1[data-oe-expression=\"blog_post.name\"]:not(:containsExact(\"\"))",
        content: Markup(_t("Set a blog post <b>cover</b>.")),
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
        trigger: "iframe #o_wblog_post_content",
        content: Markup(_t("<b>Write your story here.</b> Use the top toolbar to style your text: add an image or table, set bold or italic, etc. Drag and drop building blocks for more graphical blogs.")),
        position: "top",
        run: function (actions) {
            actions.auto();
            actions.text("Blog content", this.$anchor.find("p"));
        },
    },
    ...wTourUtils.clickOnSave(),
    {
        trigger: ".o_menu_systray_item.o_mobile_preview",
        extra_trigger: "iframe body:not(.editor_enable)",
        content: Markup(_t("Use this icon to preview your blog post on <b>mobile devices</b>.")),
        position: "bottom",
    }, {
        trigger: ".o_menu_systray_item.o_mobile_preview",
        extra_trigger: '.o_website_preview .o_is_mobile',
        content: _t("Once you have reviewed the content on mobile, you can switch back to the normal view by clicking here again"),
        position: "right",
    }, {
        trigger: '.o_menu_systray_item a:contains("Unpublished")',
        extra_trigger: "iframe body:not(.editor_enable)",
        position: "bottom",
        content: Markup(_t("<b>Publish your blog post</b> to make it visible to your visitors.")),
    },
]);
});
