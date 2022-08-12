odoo.define("website_sale.tour_shop", function (require) {
    "use strict";

    const {_t} = require("web.core");
    const {Markup} = require('web.utils');
    const wTourUtils = require("website.tour_utils");

    wTourUtils.registerEditionTour("shop", {
        url: '/shop',
        sequence: 130,
    }, [{
        trigger: ".o_menu_systray .o_new_content_container > a",
        content: _t("Let's create your first product."),
        extra_trigger: "iframe .js_sale",
        consumeVisibleOnly: true,
        position: "bottom",
    }, {
        trigger: "a[data-module-xml-id='base.module_website_sale']",
        content: Markup(_t("Select <b>New Product</b> to create it and manage its properties to boost your sales.")),
        position: "bottom",
    }, {
        trigger: ".modal-dialog input[type=text]",
        content: _t("Enter a name for your new product"),
        position: "left",
    }, {
        trigger: ".modal-footer button.btn-primary",
        content: Markup(_t("Click on <em>Save</em> to create the product.")),
        position: "right",
    }, {
        trigger: "iframe .product_price .oe_currency_value:visible",
        extra_trigger: "#oe_snippets.o_loaded",
        content: _t("Edit the price of this product by clicking on the amount."),
        position: "bottom",
        run: "text 1.99",
        timeout: 30000,
    }, {
        trigger: "iframe #wrap img.product_detail_img",
        extra_trigger: "iframe .product_price .o_dirty .oe_currency_value:not(:containsExact(1.00))",
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
        trigger: ".o_menu_systray_item .o_switch_danger_success",
        extra_trigger: "iframe body:not(.editor_enable)",
        content: _t("Click on this button so your customers can see it."),
        position: "bottom",
    }, {
        trigger: "button[data-menu-xmlid='website.menu_reporting']",
        content: _t("Click here to open the reporting menu"),
        position: "bottom",
    }, {
        trigger: "a[data-menu-xmlid='website.menu_website_dashboard'], a[data-menu-xmlid='website.menu_website_analytics']",
        content: _t("Let's now take a look at your eCommerce dashboard to get your eCommerce website ready in no time."),
        position: "bottom",
        run: "click",
    }]);
});
