odoo.define("website_sale.tour_shop", function (require) {
    "use strict";

    var core = require("web.core");
    var tour = require("web_tour.tour");
    var base = require("web_editor.base");

    var _t = core._t;

    tour.register("shop", {
        url: "/",
        wait_for: base.ready(),
    }, [tour.STEPS.WEBSITE_NEW_PAGE, {
        trigger: "a[data-action=new_product]",
        content: _t("Select <b>New Product</b> to create it and manage its properties to boost your sales."),
        position: "bottom",
    }, {
        trigger: ".modal-dialog #editor_new_product input[type=text]",
        content: _t("Enter a name for your new product"),
        position: "right",
    }, {
        trigger: ".modal-dialog button.btn-primary.btn-continue",
        content: _t("Click on <em>Continue</em> to create the product."),
        position: "right",
    }, {
        trigger: ".product_price .o_is_inline_editable .oe_currency_value",
        content: _t("Edit the price of this product by clicking on the amount."),
        position: "bottom",
        run: "text 1.99",
    }, {
        trigger: "#wrap img.product_detail_img",
        extra_trigger: ".product_price .o_is_inline_editable .oe_currency_value:not(:containsExact(1.00))",
        content: _t("Click here to set an image describing your product."),
        position: "top",
    }, {
        trigger: ".o_select_media_dialog img:first",
        content: _t("Choose an image from the library."),
        position: "bottom",
    }, {
        trigger: ".o_select_media_dialog .btn.o_save_button",
        extra_trigger: ".o_existing_attachment_cell.o_selected",
        content: _t("Click on <b>Save</b> to add the image to the product description."),
        position: "right",
    }, {
        trigger: "#snippet_structure .oe_snippet:eq(8) .oe_snippet_thumbnail",
        extra_trigger: "body:not(.modal-open)",
        content: _t("Drag this website block and drop it in your page."),
        position: "bottom",
        run: "drag_and_drop",
    }, {
        trigger: "button[data-action=save]",
        content: _t("Once you click on <b>Save</b>, your product is updated."),
        position: "bottom",
    }, {
        trigger: ".js_publish_management button.js_publish_btn.btn-danger",
        extra_trigger: "body:not(.editor_enable)",
        content: _t("Click on this button so your customers can see it."),
        position: "top",
    }, {
        trigger: ".o_web_settings_dashboard_progress_title,.progress",
        extra_trigger: "body:not(.editor_enable)",
        content: _t("Follow the steps and advices in the Odoo Planner to deploy your e-Commerce website in no time!"),
        position: "bottom",
    }]);
});
