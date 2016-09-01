odoo.define("website.tour.banner", function (require) {
    "use strict";

    var core = require("web.core");
    var tour = require("web_tour.tour");
    var base = require("web_editor.base");

    var _t = core._t;

    tour.register("banner", {
        url: "/",
        wait_for: base.ready(),
    }, [{
        trigger: "a[data-action=edit]",
        content: _t("<b>Click Edit</b> to start designing your homepage."),
        position: "bottom",
    }, {
        trigger: "#snippet_structure .oe_snippet:eq(1) .oe_snippet_thumbnail",
        content: _t("Drag the <i>Cover</i> block and drop it in your page."),
        position: "bottom",
        run: "drag_and_drop",
    }, {
        trigger: "#wrapwrap .s_text_block_image_fw h2",
        content: _t("<b>Click on a text</b> to start editing it. <i>It's that easy to edit your content!</i>"),
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


odoo.define("website.tour.contact", function (require) {
    "use strict";

    var core = require("web.core");
    var tour = require("web_tour.tour");
    var base = require("web_editor.base");
    var _t = core._t;

    tour.register("contact", {
        url: "/page/contactus",
        wait_for: base.ready(),
    }, [{
        trigger: "li#customize-menu",
        content: _t("<b>Install a contact form</b> to improve this page."),
        extra_trigger: "#o_contact_mail",
        position: "bottom",
    }, {
        trigger: "li#install_apps",
        content: _t("<b>Install new apps</b> to get more features. Let's install the <i>'Contact form'</i> app."),
        position: "bottom",
    }]);
});
