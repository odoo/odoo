odoo.define("website.tour.banner", function (require) {
"use strict";

var core = require("web.core");
var tour = require("web_tour.tour");

var _t = core._t;

tour.register("banner", {
    url: "/",
}, [{
    trigger: "a[data-action=edit]",
    content: _t("<b>Click Edit</b> to start designing your homepage."),
    extra_trigger: ".homepage",
    position: "bottom",
}, {
    trigger: "#snippet_structure .oe_snippet:eq(1) .oe_snippet_thumbnail",
    content: _t("Drag the <i>Cover</i> block and drop it in your page."),
    position: "bottom",
    run: "drag_and_drop #wrap",
}, {
    trigger: "#wrapwrap .s_cover h1",
    content: _t("<b>Click on a text</b> to start editing it. <i>It's that easy to edit your content!</i>"),
    position: "bottom",
    run: "text",
}, {
    trigger: ".o_we_customize_panel",
    extra_trigger: "#wrapwrap .s_cover h1:not(:containsExact(\"Catchy Headline\"))",
    content: _t("Customize any block through this menu. Try to change the background color of this block."),
    position: "right",
}, {
    trigger: '.o_we_add_snippet_btn',
    content: _t("Go back to the blocks menu."),
    position: 'bottom',
}, {
    trigger: "#snippet_structure .oe_snippet:eq(3) .oe_snippet_thumbnail",
    content: _t("Drag another block in your page, below the cover."),
    position: "bottom",
    run: "drag_and_drop #wrap",
}, {
    trigger: "button[data-action=save]",
    content: _t("Click the <b>Save</b> button."),
    position: "bottom",
}, {
    trigger: "a[data-action=show-mobile-preview]",
    content: _t("Good Job! You have designed your homepage. Let's check how this page looks like on <b>mobile devices</b>."),
    position: "bottom",
}, {
    trigger: ".modal-dialog:has(#mobile-viewport) button[data-dismiss=modal]",
    content: _t("After having checked how it looks on mobile, <b>close the preview</b>."),
    position: "right",
}, {
    trigger: "#new-content-menu > a",
    content: _t("<p><b>Your homepage is live.</b></p><p>Let's add a new page for your site.</p>"),
    position: "bottom",
},  {
    trigger: "a[data-action=new_page]",
    content: _t("<p><b>Click here</b> to create a new page.</p>"),
    position: "bottom",
}, {
    trigger: ".modal-dialog #editor_new_page input[type=text]",
    content: _t("<p>Enter a title for the page.</p>"),
    position: "bottom",
}, {
    trigger: ".modal-footer button.btn-primary.btn-continue",
    content: _t("Click on <b>Continue</b> to create the page."),
    position: "bottom",
}, {
    trigger: "#snippet_structure .oe_snippet:eq(3) .oe_snippet_thumbnail",
    content: _t("Drag the block and drop it in your new page."),
    position: "bottom",
    run: "drag_and_drop #wrap",
}, {
    trigger: "button[data-action=save]",
    content: _t("Click the <b>Save</b> button."),
    position: "bottom",
}, {
    trigger: ".js_publish_management .js_publish_btn",
    content: _t("<b>That's it!</b><p>Your page is all set to go live. Click the <b>Publish</b> button to publish it on the website.</p>"),
    position: "bottom",
}]);
});

//==============================================================================

odoo.define("website.tour.contact", function (require) {
"use strict";

var core = require("web.core");
var tour = require("web_tour.tour");
var _t = core._t;

tour.register("contact", {
    url: "/page/contactus",
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
