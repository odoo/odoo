(function () {
    'use strict';

    var website = openerp.website;

    website.EditorBar.include({
        start: function () {
            this.registerTour(new website.EditorShopTour(this));
            var res = this._super();
            this.registerTour(new website.EditorShopTest(this));
            return res;
        },
    });

    website.EditorShopTour = website.Tour.extend({
        id: 'shop',
        name: "Create a product",
        init: function (editor) {
            var self = this;
            self.steps = [
                {
                    stepId:    'welcome-shop',
                    title:     "Welcome to your shop",
                    content:   "You successfully installed the e-commerce. This guide will help you to create your product and promote your sales.",
                    template:  self.popover({ next: "Start Tutorial", end: "Skip It" }),
                    backdrop:  true,
                },
                {
                    stepId:    'content-menu',
                    element:   '#content-menu-button',
                    placement: 'left',
                    title:     "Create your first product",
                    content:   "Click here to add a new product.",
                    template:  self.popover({ fixed: true }),
                    trigger:   'click',
                },
                {
                    stepId:    'edit-entry',
                    element:   '#create-new-product',
                    placement: 'left',
                    title:     "Create a new product",
                    content:   "Select 'New Product' to create it and manage its properties to boost your sales.",
                    template:  self.popover({ fixed: true }),
                    trigger: {
                        modal: {
                            stopOnClose: true,
                        },
                    },
                },
                {
                    stepId:    'enter-name',
                    element:   '.modal input[type=text]',
                    sampleText: 'New Product',
                    placement: 'right',
                    title:     "Choose name",
                    content:   "Enter a name for your new product then click 'Continue'.",
                    trigger:   'keyup',
                },
                {
                    stepId:    'continue-name',
                    element:   '.modal button.btn-primary',
                    placement: 'right',
                    title:     "Create Product",
                    content:   "Click <em>Continue</em> to create the product.",
                    trigger:   'reload',
                },
                {
                    stepId:    'product-page',
                    title:     "New product created",
                    content:   "This page contains all the information related to the new product.",
                    template:  self.popover({ next: "OK" }),
                },
                {
                    stepId:    'edit-price-cke',
                    element:   '.product_price .oe_currency_value',
                    sampleText: '20.50',
                    placement: 'left',
                    title:     "Change the price",
                    content:   "Edit the price of this product by clicking on the amount.",
                    template:  self.popover({ next: "OK" }),
                },
                {
                    stepId:    'update-image',
                    element:   '#wrap img.img:first',
                    placement: 'top',
                    title:     "Update image",
                    content:   "Click here to set an image describing your product.",
                    triggers: function (callback) {
                        var self = this;
                        $(self.element).on('mouseenter', function () {
                            $(this).off('mouseenter');
                            setTimeout(function () {
                                (callback || self.tour.moveToNextStep).apply(self.tour);
                            },0);
                        });
                    },
                },
                {
                    stepId:    'update-image-button',
                    element:   'button.hover-edition-button:visible',
                    placement: 'top',
                    title:     "Update image",
                    content:   "Click here to set an image describing your product.",
                    trigger:   'click',
                },
                {
                    stepId:    'upload-image',
                    element:   '.well a.pull-right',
                    placement: 'bottom',
                    title:     "Select an Image",
                    content:   "Let's select an existing image.",
                    template:  self.popover({ fixed: true }),
                    trigger:   'ajax'
                },
                {
                    stepId:    'select-image',
                    element:   'img[alt=imac]',
                    placement: 'bottom',
                    title:     "Select an Image",
                    content:   "Let's select an imac image.",
                    template:  self.popover({ fixed: true }),
                    triggers: function (callback) {
                        var self = this;
                        var click = function () {
                            $('.modal-dialog.select-image img').off('click', click);
                            setTimeout(function () {
                                (callback || self.tour.moveToNextStep).apply(self.tour);
                            },0);
                        };
                        $('.modal-dialog.select-image img').on('click', click);
                    },
                },
                {
                    stepId:    'save-image',
                    element:   'button.save',
                    placement: 'bottom',
                    title:     "Select this Image",
                    content:   "Click to add the image to the product decsription.",
                    template:  self.popover({ fixed: true }),
                    trigger:   'click',
                },
                {
                    stepId:    'add-block',
                    element:   'button[data-action=snippet]',
                    placement: 'bottom',
                    title:     "Describe the Product",
                    content:   "Insert blocks like text-image, or gallery to fully describe the product.",
                    template:  self.popover({ fixed: true }),
                    trigger:   'click',
                },
                {
                    stepId:    'drag-big-picture',
                    snippet:   'big-picture',
                    placement: 'bottom',
                    title:     "Drag & Drop a block",
                    content:   "Drag the 'Big Picture' block and drop it in your page.",
                    template:  self.popover({ fixed: true }),
                    trigger:   'drag',
                },
                {
                    stepId:    'save-changes',
                    element:   'button[data-action=save]',
                    placement: 'right',
                    title:     "Save your modifications",
                    content:   "Once you click on save, your product is updated.",
                    template:  self.popover({ fixed: true }),
                    trigger:   'reload',

                },
                {
                    stepId:    'publish-product',
                    element:   '.js_publish_management button.js_publish_btn.btn-danger',
                    placement: 'top',
                    title:     "Publish your product",
                    content:   "Click to publish your product so your customers can see it.",
                    trigger:   'ajax'
                },
                {
                    stepId:    'congratulations',
                    title:     "Congratulations",
                    content:   "Congratulations! You just created and published your first product.",
                    template:  self.popover({ end: "Close Tutorial" }),
                    backdrop:  true,
                },
            ];
            return this._super();
        },
        trigger: function () {
            return (this.resume() && this.testUrl(/^\/shop\/product\/[0-9]+\//)) || this._super();
        },
    });


    website.Test = website.Tour.extend({
        registerStep: function (step) {
            var self = this;
            var step = this._super(step);
            if (step.beforeTrigger || step.afterTrigger) {
                var fn = step.triggers;
                step.triggers = function (callback) {
                    if (step.beforeTrigger) step.beforeTrigger(self);
                    if (!step.afterTrigger) {
                        fn.call(step, callback);
                    } else {
                        fn.call(step, function () {
                            (callback || self.moveToNextStep).apply(self);
                             step.afterTrigger(self);
                        });
                    }
                };
            }
            return step;
        }
    });


    website.EditorShopTest = website.Test.extend({
        id: 'shop_buy_product',
        name: "Try to buy products",
        path: '/shop',
        init: function (editor) {
            var self = this;
            self.steps = [
                {
                    stepId:    'begin-test',
                    title:     'begin-test',
                    template:  self.popover({ next: "Start Test"}),
                    backdrop:  true,
                },
                {
                    stepId:    'display-ipod',
                    element:   '.oe_product_cart a:contains("iPod")',
                    trigger: {
                        url:   /shop\/product\/.*/,
                    },
                },
                {
                    stepId:    'choose-ipod',
                    element:   'input[name="product_id"]:not([checked])',
                    trigger:   'mouseup',
                },
                {
                    stepId:    'add-ipod',
                    element:   'form[action="/shop/add_cart/"] button',
                    trigger: {
                        url:   '/shop/mycart/',
                    },
                },
                {
                    stepId:    'add-suggested-product',
                    element:   'form[action="/shop/add_cart/"] button:contains("Add to Cart")',
                    trigger:   'reload',
                },
                {
                    stepId:    'more-product',
                    element:   '.oe_mycart a.js_add_cart_json:eq(1)',
                    trigger:   'ajax',
                },
                {
                    stepId:    'less-product',
                    element:   '.oe_mycart a.js_add_cart_json:eq(2)',
                    trigger:   'reload',
                },
                {
                    stepId:    'number-product',
                    element:   '.oe_mycart input.js_quantity',
                    sampleText: '1',
                    trigger:   'reload',
                },
                {
                    stepId:    'go-checkout-product',
                    element:   'a[href="/shop/checkout/"]',
                    trigger: {
                        url:   '/shop/checkout/',
                    },
                },
                {
                    stepId:    'confirm-false-checkout-product',
                    element:   'form[action="/shop/confirm_order/"] button',
                    trigger: {
                        url:   '/shop/confirm_order/',
                    },
                    beforeTrigger: function (tour) {
                        $("input[name='phone']").val("");
                    },
                },
                {
                    stepId:    'confirm-checkout-product',
                    element:   'form[action="/shop/confirm_order/"] button',
                    trigger: {
                        url:   '/shop/payment/',
                    },
                    beforeTrigger: function (tour) {
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
                    stepId:    'acquirer-checkout-product',
                    element:   'input[name="acquirer"]',
                    trigger:   'mouseup',
                },
                {
                    stepId:    'pay-checkout-product',
                    element:   'button:contains("Pay Now")',
                    trigger: {
                        url:   /shop\/confirmation\//,
                    },
                    afterTrigger: function (tour) {
                        console.log('{ "event": "success" }');
                    },
                }
            ];
            return this._super();
        },
        trigger: function () {
            return (this.resume() && this.testUrl(/\/shop\//)) || this._super();
        },
    });

}());
