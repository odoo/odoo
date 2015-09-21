odoo.define('website_sale.tour_shop', function (require) {
'use strict';

var core = require('web.core');
var Tour = require('web.Tour');
var base = require('web_editor.base');
var website = require('website.website');

var _t = core._t;

base.ready().done(function () {
    Tour.register({
        id: 'shop',
        name: _t("Create a product"),
        steps: [
            {
                title:     _t("Welcome to your shop"),
                content:   _t("You successfully installed the e-commerce. This guide will help you to create your product and promote your sales."),
                popover:   { next: _t("Start Tutorial"), end: _t("Skip It") },
            },
            {
                element:   '#content-menu-button',
                placement: 'left',
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
                element:   '.product_price .oe_currency_value:visible',
                sampleText: '20.50',
                placement: 'left',
                title:     _t("Change the price"),
                content:   _t("Edit the price of this product by clicking on the amount."),
            },
            {
                waitNot:   '.product_price .oe_currency_value:visible:containsExact(1.00)',
                element:   '#wrap img.product_detail_img',
                placement: 'top',
                title:     _t("Update image"),
                content:   _t("Click here to set an image describing your product."),
            },
            {
                element:   '.modal .existing-attachment-cell:nth(2) img',
                placement: 'top',
                title:     _t("Choose an image"),
                content:   _t("Choose an image from the library."),
                popover:   { fixed: true },
                onload: function () {
                    $('form[action="/web_editor/attachment/add"] .well > *').hide();
                }
            },
            {
                element:   '.modal .btn.save',
                placement: 'right',
                waitFor:   '.existing-attachment-cell.media_selected',
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
                placement: 'right',
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
});

});
