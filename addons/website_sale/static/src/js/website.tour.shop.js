(function () {
    'use strict';

    var _t = openerp._t;

    openerp.Tour.register({
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
                content:   _t("Select 'New Product' to create it and manage its properties to boost your sales."),
                popover:   { fixed: true },
            },
            {
                element:   '.modal #editor_new_product input[type=text]',
                sampleText: 'New Product',
                placement: 'right',
                title:     _t("Choose name"),
                content:   _t("Enter a name for your new product then click 'Continue'."),
            },
            {
                waitNot:   '.modal input[type=text]:not([value!=""])',
                element:   '.modal button.btn-primary',
                placement: 'right',
                title:     _t("Create Product"),
                content:   _t("Click <em>Continue</em> to create the product."),
            },
            {
                waitFor:   'body:has(button[data-action=save]:visible):has(.js_sale)',
                title:     _t("New product created"),
                content:   _t("This page contains all the information related to the new product."),
                popover:   { next: _t("Continue") },
            },
            {
                element:   '.product_price .oe_currency_value',
                sampleText: '20.50',
                placement: 'left',
                title:     _t("Change the price"),
                content:   _t("Edit the price of this product by clicking on the amount."),
            },


            {
                waitNot:   '.product_price .oe_currency_value:containsExact(1.00)',
                element:   '#wrap img.product_detail_img',
                placement: 'top',
                title:     _t("Update image"),
                content:   _t("Click here to set an image describing your product."),
            },
            {
                element:   'img[alt=ipad]',
                placement: 'top',
                title:     _t("Select an Image"),
                content:   _t("Let's select an ipad image."),
            },
            {
                waitFor:   '.media_selected img[alt=ipad]',
                element:   '.modal-content button.save',
                placement: 'top',
                title:     _t("Save this Image"),
                content:   _t("Click on save to add the image to the product decsription."),
            },
            {
                waitNot:   '.modal-content:visible',
                element:   'button[data-action=snippet]',
                placement: 'bottom',
                title:     _t("Describe the Product"),
                content:   _t("Insert blocks like text-image, or gallery to fully describe the product."),
                popover:   { fixed: true },
            },
            {
                snippet:   '#snippet_structure .oe_snippet:eq(7)',
                placement: 'bottom',
                title:     _t("Drag & Drop a block"),
                content:   _t("Drag the 'Big Picture' block and drop it in your page."),
                popover:   { fixed: true },
            },
            {
                element:   'button[data-action=save]',
                placement: 'right',
                title:     _t("Save your modifications"),
                content:   _t("Once you click on save, your product is updated."),
                popover:   { fixed: true },
            },
            {
                waitFor:   '#website-top-navbar button[data-action="edit"]:visible',
                element:   '.js_publish_management button.js_publish_btn.btn-danger',
                placement: 'top',
                title:     _t("Publish your product"),
                content:   _t("Click to publish your product so your customers can see it."),
            },
            {
                waitFor:   '.js_publish_management button.js_publish_btn.btn-success:visible',
                title:     _t("Congratulations"),
                content:   _t("Congratulations! You just created and published your first product."),
                popover:   { next: _t("Close Tutorial") },
            },
        ]
    });

}());
