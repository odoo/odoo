odoo.define("website_sale.tour_shop", function (require) {
    "use strict";

    const {_t} = require("web.core");
    const {Markup} = require('web.utils');

    // return the steps, used for backend and frontend

    return [{
        trigger: "body:has(#o_new_content_menu_choices.o_hidden) #new-content-menu > a",
        content: _t("Let's create your first product."),
        extra_trigger: ".js_sale",
        consumeVisibleOnly: true,
        position: "bottom",
    }, {
        trigger: "a[data-action=new_product]",
        content: Markup(_t("Select <b>New Product</b> to create it and manage its properties to boost your sales.")),
        position: "bottom",
    }, {
        trigger: ".modal-dialog #editor_new_product input[type=text]",
        content: _t("Enter a name for your new product"),
        position: "left",
    }, {
        trigger: ".modal-footer button.btn-primary.btn-continue",
        content: Markup(_t("Click on <em>Continue</em> to create the product.")),
        position: "right",
    }, {
        trigger: ".product_price .oe_currency_value:visible",
        extra_trigger: ".editor_enable",
        content: _t("Edit the price of this product by clicking on the amount."),
        position: "bottom",
        run: "text 1.99",
    }, {
        trigger: "#wrap img.product_detail_img",
        extra_trigger: ".product_price .o_dirty .oe_currency_value:not(:containsExact(1.00))",
        content: _t("Double click here to set an image describing your product."),
        position: "top",
        run: function (actions) {
            actions.dblclick();
        },
    }, {
        trigger: ".o_select_media_dialog .o_upload_media_button",
        content: _t("Upload a file from your local library."),
        position: "bottom",
        run: function (actions) {
            actions.auto(".modal-footer .btn-secondary");
        },
        auto: true,
    }, {
        trigger: "button.o_we_add_snippet_btn",
        auto: true,
    }, {
        trigger: "#snippet_structure .oe_snippet:eq(3) .oe_snippet_thumbnail",
        extra_trigger: "body:not(.modal-open)",
        content: _t("Drag this website block and drop it in your page."),
        position: "bottom",
        run: "drag_and_drop",
    }, {
        trigger: "button[data-action=save]",
        content: Markup(_t("Once you click on <b>Save</b>, your product is updated.")),
        position: "bottom",
    }, {
        trigger: ".js_publish_management .js_publish_btn .css_publish",
        extra_trigger: "body:not(.editor_enable)",
        content: _t("Click on this button so your customers can see it."),
        position: "bottom",
    }, {
        trigger: ".o_main_navbar .o_menu_toggle, #oe_applications .dropdown-toggle",
        content: _t("Let's now take a look at your administration dashboard to get your eCommerce website ready in no time."),
        position: "bottom",
    }, { // backend
        trigger: '.o_apps > a[data-menu-xmlid="website.menu_website_configuration"], #oe_main_menu_navbar a[data-menu-xmlid="website.menu_website_configuration"]',
        content: _t("Open your website app here."),
        extra_trigger: ".o_apps,#oe_applications",
        position: "bottom",
        timeout: 30000, // ~ 10 secondes to be redirected, due to slow assets generation
    }];
});
