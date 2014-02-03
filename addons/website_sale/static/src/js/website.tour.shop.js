(function () {
    'use strict';

    var website = openerp.website;

    website.EditorBar.include({
        start: function () {
            this.registerTour(new website.EditorShopTour(this));
            var res = this._super();
            return res;
        },
    });

    website.EditorShopTour = website.Tour.extend({
        id: 'shop',
        name: "Create a product",
        testPath: /\/shop\/.*/,
        init: function (editor) {
            var self = this;
            self.steps = [
                {
                    title:     "Welcome to your shop",
                    content:   "You successfully installed the e-commerce. This guide will help you to create your product and promote your sales.",
                    template:  self.popover({ next: "Start Tutorial", end: "Skip It" }),
                },
                {
                    element:   '#content-menu-button',
                    placement: 'left',
                    title:     "Create your first product",
                    content:   "Click here to add a new product.",
                    template:  self.popover({ fixed: true }),
                },
                {
                    element:   'a[data-action=new_product]',
                    placement: 'left',
                    title:     "Create a new product",
                    content:   "Select 'New Product' to create it and manage its properties to boost your sales.",
                    template:  self.popover({ fixed: true }),
                },
                {
                    element:   '.modal:contains("New Product") input[type=text]',
                    sampleText: 'New Product',
                    placement: 'right',
                    title:     "Choose name",
                    content:   "Enter a name for your new product then click 'Continue'.",
                },
                {
                    waitNot:   '.modal input[type=text]:not([value!=""])',
                    element:   '.modal button.btn-primary',
                    placement: 'right',
                    title:     "Create Product",
                    content:   "Click <em>Continue</em> to create the product.",
                },
                {
                    waitFor:   '#website-top-navbar button[data-action="save"]:visible',
                    title:     "New product created",
                    content:   "This page contains all the information related to the new product.",
                    template:  self.popover({ next: "Continue" }),
                },
                {
                    element:   '.product_price .oe_currency_value',
                    sampleText: '20.50',
                    placement: 'left',
                    title:     "Change the price",
                    content:   "Edit the price of this product by clicking on the amount.",
                },
                {
                    waitNot:   '.product_price .oe_currency_value:containsExact(1.00)',
                    element:   '#wrap img.img:first',
                    placement: 'top',
                    title:     "Update image",
                    content:   "Click here to set an image describing your product.",
                },
                {
                    element:   'button.hover-edition-button:visible',
                    placement: 'top',
                    title:     "Update image",
                    content:   "Click here to set an image describing your product.",
                },
                {
                    wait:      500,
                    element:   '.well a.pull-right',
                    placement: 'bottom',
                    title:     "Select an Image",
                    content:   "Let's select an existing image.",
                    template:  self.popover({ fixed: true }),
                },
                {
                    element:   'img[alt=imac]',
                    placement: 'bottom',
                    title:     "Select an Image",
                    content:   "Let's select an imac image.",
                    template:  self.popover({ fixed: true }),
                },
                {
                    waitNot:   'img[alt=imac]',
                    element:   '.modal-content button.save',
                    placement: 'bottom',
                    title:     "Select this Image",
                    content:   "Click to add the image to the product decsription.",
                    template:  self.popover({ fixed: true }),
                },
                {
                    waitNot:   '.modal-content:visible',
                    element:   'button[data-action=snippet]',
                    placement: 'bottom',
                    title:     "Describe the Product",
                    content:   "Insert blocks like text-image, or gallery to fully describe the product.",
                    template:  self.popover({ fixed: true }),
                },
                {
                    snippet:   'big-picture',
                    placement: 'bottom',
                    title:     "Drag & Drop a block",
                    content:   "Drag the 'Big Picture' block and drop it in your page.",
                    template:  self.popover({ fixed: true }),
                },
                {
                    element:   'button[data-action=save]',
                    placement: 'right',
                    title:     "Save your modifications",
                    content:   "Once you click on save, your product is updated.",
                    template:  self.popover({ fixed: true }),

                },
                {
                    waitFor:   '#website-top-navbar button[data-action="edit"]:visible',
                    element:   '.js_publish_management button.js_publish_btn.btn-danger',
                    placement: 'top',
                    title:     "Publish your product",
                    content:   "Click to publish your product so your customers can see it.",
                },
                {
                    waitFor:   '.js_publish_management button.js_publish_btn.btn-success:visible',
                    title:     "Congratulations",
                    content:   "Congratulations! You just created and published your first product.",
                    template:  self.popover({ next: "Close Tutorial" }),
                },
            ];
            return this._super();
        }
    });

    website.EditorShopTest = website.Tour.extend({
        id: 'shop_buy_product',
        name: "Try to buy products",
        path: '/shop',
        testPath: /\/shop/,
        init: function (editor) {
            var self = this;
            self.steps = [
                {
                    title:     'begin-test',
                    template:  self.popover({ next: "Start Test"}),
                    backdrop:  true,
                },
                {
                    title:     "select ipod",
                    element:   '.oe_product_cart a:contains("iPod")',
                },
                {
                    title:     "select ipod 32Go",
                    element:   'input[name="product_id"]:not([checked])',
                },
                {
                    title:     "click on add to cart",
                    waitFor:   'input[name="product_id"]:eq(1)[checked]',
                    element:   'form[action="/shop/add_cart/"] button',
                },
                {
                    title:     "add suggested",
                    element:   'form[action="/shop/add_cart/"] button.btn-link:contains("Add to Cart")',
                },
                {
                    title:     "add one more iPod",
                    waitFor:   '.my_cart_quantity:contains(2)',
                    element:   '#mycart_products tr:contains("iPod: 32 Gb") a.js_add_cart_json:eq(1)',
                },
                {
                    title:     "remove Headphones",
                    waitFor:   '#mycart_products tr:contains("iPod: 32 Gb") input.js_quantity[value=2]',
                    element:   '#mycart_products tr:contains("Apple In-Ear Headphones") a.js_add_cart_json:first',
                },
                {
                    title:     "set one iPod",
                    waitNot:   '#mycart_products tr:contains("Apple In-Ear Headphones")',
                    element:   '#mycart_products input.js_quantity',
                    sampleText: '1',
                },
                {
                    title:     "go to checkout",
                    waitFor:   '#mycart_products input.js_quantity[value=1]',
                    element:   'a[href="/shop/checkout/"]',
                },
                {
                    title:     "test with input error",
                    element:   'form[action="/shop/confirm_order/"] button',
                    callback: function (tour) {
                        $("input[name='phone']").val("");
                    },
                },
                {
                    title:     "test without input error",
                    waitFor:   'form[action="/shop/confirm_order/"] .has-error',
                    element:   'form[action="/shop/confirm_order/"] button',
                    callback: function (tour) {
                        if ($("input[name='name']").val() === "")
                            $("input[name='name']").val("website_sale-test-shoptest");
                        if ($("input[name='email']").val() === "")
                            $("input[name='email']").val("website_sale-test-shoptest@website_sale-test-shoptest.optenerp.com");
                        $("input[name='phone']").val("123");
                        $("input[name='street']").val("123");
                        $("input[name='city']").val("123");
                        $("input[name='zip']").val("123");
                        $("select[name='country_id']").val("21");
                    },
                },
                {
                    title:     "select acquirer",
                    element:   'input[name="acquirer"]',
                },
                {
                    title:     "confirm",
                    element:   'button:contains("Pay Now")',
                },
                {
                    title:     "finish",
                    waitFor:   '.oe_website_sale:contains("Thank you for your order")',
                }
            ];
            return this._super();
        },
    });
    // for test without editor bar
    $(document).ready(function () {
        website.Tour.add(website.EditorShopTest);
    });

}());
