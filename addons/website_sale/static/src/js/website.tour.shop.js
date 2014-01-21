(function () {
    'use strict';

    var website = openerp.website;

    website.EditorBar.include({
        start: function () {
            this.registerTour(new website.EditorShopTour(this));
            this.registerTour(new website.EditorShopTest(this));
            return this._super();
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
                            afterSubmit: 'product-page',
                        },
                    },
                },
                {
                    stepId:    'enter-name',
                    element:   '.modal input[type=text]',
                    placement: 'right',
                    title:     "Choose name",
                    content:   "Enter a name for your new product then click 'Continue'.",
                },
                {
                    stepId:    'product-page',
                    title:     "New product created",
                    content:   "This page contains all the information related to the new product.",
                    template:  self.popover({ next: "OK" }),
                    backdrop:  true,
                },
                {
                    stepId:    'edit-price',
                    element:   '.product_price',
                    placement: 'left',
                    title:     "Change the public price",
                    content:   "Edit the sale price of this product by clicking on the amount. The price is the sale price used in all sale orders when selling this product.",
                    template:  self.popover({ next: "OK" }),
                },
                {
                    stepId:    'update-image',
                    element:   '#wrap img.img:first',
                    placement: 'top',
                    title:     "Update image",
                    content:   "Click here to set an image describing your product.",
                    triggers: function () {
                        function registerClick () {
                            $('button.hover-edition-button').one('click', function () {
                                $('#wrap img.img:first').off('hover', registerClick);
                                self.moveToNextStep();
                            });
                        }
                        $('#wrap img.img:first').on('hover', registerClick);

                    },
                },
                {
                    stepId:    'upload-image',
                    element:   'button.filepicker',
                    placement: 'left',
                    title:     "Upload image",
                    content:   "Click on 'Upload an image from your computer' to pick an image describing your product.",
                    template:  self.popover({ next: "OK" }),
                    triggers: function () {
                        $(document).on('hide.bs.modal', function () {
                            self.moveToStep('add-block');
                        });
                    }
                },
                {
                    stepId:    'save-image',
                    element:   'button.save',
                    placement: 'right',
                    title:     "Save the image",
                    content:   "Click 'Save Changes' to add the image to the product decsription.",
                },
                {
                    stepId:    'add-block',
                    element:   'button[data-action=snippet]',
                    placement: 'bottom',
                    title:     "Describe the product for your audience",
                    content:   "Insert blocks like text-image, or gallery to fully describe the product and make your visitors want to buy this product.",
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
                    trigger:   'click',

                },
                {
                    stepId:    'publish-product',
                    element:   '.js_publish_management button.js_publish_btn.btn-danger',
                    placement: 'top',
                    title:     "Publish your product",
                    content:   "Click to publish your product so your customers can see it.",
                    trigger:   'click',
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
        id: 'shoptest',
        name: "Try to by 3 products",
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
                    trigger: {
                        id: 'mouseup',
                    },
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
                    trigger:   'click',
                },
                {
                    stepId:    'less-product',
                    element:   '.oe_mycart a.js_add_cart_json:eq(2)',
                    trigger:   'reload',
                },
                {
                    stepId:    'number-product',
                    element:   '.oe_mycart input.js_quantity',
                    trigger:   'reload',
                    beforeTrigger: function (tour) {
                        if (parseInt($(".oe_mycart input.js_quantity").val(),10) !== 1)
                            $(".oe_mycart input.js_quantity").val("1").change();
                    },
                    afterTrigger: function (tour) {
                        if ($(".oe_mycart input.js_quantity").size() !== 1)
                            throw "Can't remove suggested item from my cart";
                        if (parseInt($(".oe_mycart input.js_quantity").val(),10) !== 1)
                            throw "Can't defined number of items in my cart";
                    },
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
                        window.localStorage.setItem("test-success", "{}");
                    },
                },
                {
                    stepId:    'end-test',
                    backdrop:  true,
                },
            ];
            return this._super();
        },
        trigger: function () {
            return (this.resume() && this.testUrl(/^\/shop\//)) || this._super();
        },
    });

}());
