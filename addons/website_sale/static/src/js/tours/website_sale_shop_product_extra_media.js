odoo.define("website_sale.tour_shop_create_product_extra_media", function (require) {
"use strict";

var core = require("web.core");
var tour = require('web_tour.tour');
var _t = core._t;

tour.register("shop_create_product_extra_media", {
    url: "/shop",
}, [{
    trigger: "#new-content-menu > a",
    content: _t("Let's create your first product."),
    extra_trigger: ".js_sale",
    position: "bottom",
}, {
    trigger: "a[data-action=new_product]",
    content: _t("Select <b>New Product</b> to create it and manage its properties to boost your sales."),
    position: "bottom",
}, {
    trigger: ".modal-dialog #editor_new_product input[type=text]",
    content: _t("Enter a name for your new product"),
    position: "right",
}, {
    trigger: ".modal-footer button.btn-primary.btn-continue",
    content: _t("Click on <em>Continue</em> to create the product."),
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
}, {
    trigger: "button.o_we_add_snippet_btn",
    auto: true,
}, {
    trigger: "#wrap li.o_wsale_product_add_media",
    extra_trigger: ".product_price .o_dirty .oe_currency_value:not(:containsExact(1.00))",
    content: _t("Double click here to set an image as product extra media."),
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
}, {
    trigger: "button[data-action=save]",
    content: _t("Once you click on <b>Save</b>, your product is updated."),
    position: "bottom",
}]);

});
