odoo.define("website_sale.tour_shop", function (require) {
    "use strict";

    var core = require("web.core");
    var Tour = require("web.Tour");
    var tour = require("web_tour.tour");
    var base = require("web_editor.base");

    var _t = core._t;

    base.ready().done(function () {
        Tour.register({
            id: 'shop',
            mode: 'test',
            name: _t("Create a product"),
            steps: [
                {
                    title:     _t("Welcome to your shop"),
                    content:   _t("You successfully installed the e-commerce. This guide will help you to create your product and promote your sales."),
                    popover:   { next: _t("Start Tutorial"), end: _t("Skip It") },
                },
                {
                    element:   '#oe_main_menu_navbar a[data-action=new_page]',
                    placement: 'bottom',
                    title:     _t("Create your first product"),
                    content:   _t("Click here to add a new product."),
                    popover:   { fixed: true },
                },
                {
                    element:   'a[data-action=new_product]',
                    placement: 'left',
                    title:     _t("Create a new product"),
                    content:   _t("Select <em>New Product</em> to create it and manage its properties to boost your sales."),
                    popover:   { fixed: true },
                },
                {
                    element:   '.modal-dialog #editor_new_product input[type=text]',
                    sampleText: 'New Product',
                    placement: 'right',
                    title:     _t("Choose name"),
                    content:   _t("Enter a name for your new product"),
                },
                {
                    waitNot:   '.modal-dialog #editor_new_product input[type=text]:not([value!=""])',
                    element:   '.modal-dialog button.btn-primary.btn-continue',
                    placement: 'right',
                    title:     _t("Create Product"),
                    content:   _t("Click on <em>Continue</em> to create the product."),
                },
                {
                    waitFor:   '#o_scroll .oe_snippet',
                    title:     _t("New product created"),
                    content:   _t("This page contains all the information related to the new product."),
                    popover:   { next: _t("Continue") },
                },
                {
                    element:   '.product_price .oe_currency_value:visible:first',
                    sampleText: '20.50',
                    placement: 'bottom',
                    title:     _t("Change the price"),
                    content:   _t("Edit the price of this product by clicking on the amount."),
                },
                {
                    waitNot:   '.product_price .oe_currency_value:visible:first:containsExact(1.00)',
                    element:   '#wrap img.product_detail_img',
                    placement: 'top',
                    title:     _t("Update image"),
                    content:   _t("Click here to set an image describing your product."),
                },
                {
                    element:   '.modal .o_existing_attachment_cell:nth(2) img',
                    placement: 'top',
                    title:     _t("Choose an image"),
                    content:   _t("Choose an image from the library."),
                    popover:   { fixed: true },
                    onload: function () {
                        $('form[action="/web_editor/attachment/add"] .well > *').hide();
                    }
                },
                {
                    element:   '.modal .btn.o_save_button',
                    placement: 'right',
                    waitFor:   '.o_existing_attachment_cell.o_selected',
                    title:       _t("Save"),
                    content:     _t("Click on <em>Save</em> to add the image to the product description."),
                },
                {
                    waitNot:   '.modal-content:visible',
                    snippet:   '#snippet_structure .oe_snippet:eq(8)',
                    placement: 'bottom',
                    title:     _t("Drag & Drop a block"),
                    content:   _t("Drag this website block and drop it in your page."),
                    popover:   { fixed: true },
                },
                {
                    element:   'button[data-action=save]',
                    placement: 'bottom',
                    title:     _t("Save your modifications"),
                    content:   _t("Once you click on <em>Save</em>, your product is updated."),
                    popover:   { fixed: true },
                },
                {
                    waitNot:   '#web_editor-top-edit',
                    element:   '.js_publish_management button.js_publish_btn.btn-danger',
                    placement: 'top',
                    title:     _t("Publish your product"),
                    content:   _t("Click on <em>Publish</em> your product so your customers can see it."),
                },
                {
                    waitFor:   '.js_publish_management button.js_publish_btn.btn-success:visible',
                    title:     _t("Congratulations"),
                    content:   _t("Congratulations! You just created and published your first product."),
                    popover:   { next: _t("Close Tutorial") },
                },
            ]
        });

        tour.register("shop", {
            skip_enabled: true,
            url: "/shop",
        }, [{
            trigger: "#oe_main_menu_navbar a[data-action=new_page]",
            content: _t("You successfully installed the e-commerce.<br/>Click here to add a new product."),
            position: "bottom",
        }, {
            trigger: "a[data-action=new_product]",
            content: _t("Select <b>New Product</b> to create it and manage its properties to boost your sales."),
            position: "left",
        }, {
            trigger: ".modal-dialog #editor_new_product input[type=text]",
            content: _t("Enter a name for your new product"),
            position: "right",
        }, {
            trigger: ".modal-dialog button.btn-primary.btn-continue",
            extra_trigger: ".modal-dialog #editor_new_product input[type=text][value!=\"\"]",
            content: _t("Click on <em>Continue</em> to create the product."),
            position: "right",
        }, {
            trigger: ".product_price .oe_currency_value:visible:first",
            content: _t("Edit the price of this product by clicking on the amount."),
            position: "bottom",
        }, {
            trigger: "#wrap img.product_detail_img",
            extra_trigger: ".product_price .oe_currency_value:visible:first:not(:containsExact(1.00))",
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
            trigger: "#snippet_structure .oe_snippet:eq(8)",
            extra_trigger: "body:not(.modal-open)",
            content: _t("Drag this website block and drop it in your page."),
            position: "bottom",
        }, {
            trigger: "button[data-action=save]",
            content: _t("Once you click on <b>Save</b>, your product is updated."),
            position: "bottom",
        }, {
            trigger: ".js_publish_management button.js_publish_btn.btn-danger",
            extra_trigger: "body:not(.editor_enable)",
            content: _t("Click on this button so your customers can see it."),
            position: "top",
        }]);
    });
});
