odoo.define("website.tour.banner", function (require) {
    "use strict";

    var core = require("web.core");
    var tour = require("web_tour.tour");
    var base = require("web_editor.base");

    var _t = core._t;

    base.ready().done(function () {
        tour.register("banner", {
            url: "/",
        }, [{
            trigger: "a[data-action=edit]",
            content: _t("Every page of your website can be modified through the <b>Edit</b> button."),
            position: "bottom",
        }, {
            trigger: "#snippet_structure .oe_snippet:eq(1) .oe_snippet_thumbnail",
            content: _t("Drag the Cover block and drop it in your page."),
            position: "bottom",
            run: "drag_and_drop",
        }, {
            trigger: "#wrapwrap .s_text_block_image_fw h2",
            content: _t("Click in the title text and start editing it."),
            position: "left",
            width: 150,
            run: "text",
        }, {
            trigger: ".oe_overlay_options .oe_options",
            extra_trigger: "#wrapwrap .s_text_block_image_fw h2:not(:containsExact(\"Headline\"))",
            content: _t("Customize any block through this menu. Try to change the background of the banner."),
            position: "bottom",
        }, {
            trigger: "#snippet_structure .oe_snippet:eq(3) .oe_snippet_thumbnail",
            content: _t("Drag another block in your page, below the cover."),
            position: "bottom",
            run: "drag_and_drop",
        }, {
            trigger: "button[data-action=save]",
            extra_trigger: ".oe_overlay_options .oe_options",
            content: _t("Publish your page by clicking on the <b>Save</b> button."),
            position: "bottom",
        }, {
            trigger: "a[data-action=show-mobile-preview]",
            content: _t("Good Job! You created your first page. Let's check how this page looks like on <b>mobile devices</b>."),
            position: "bottom",
        }, {
            trigger: ".modal-dialog:has(#mobile-viewport) button[data-dismiss=modal]",
            content: _t("After having checked how it looks on mobile, <b>close the preview</b>."),
            position: "right",
        }, {
            trigger: "#oe_main_menu_navbar a[data-action=new_page]",
            content: _t("<p><b>That's it.</b> Your homepage is live.</p><p>Continue adding more pages to your site or edit this page to make it even more awesome.</p>"),
            position: "bottom",
        }]);
    });
});
