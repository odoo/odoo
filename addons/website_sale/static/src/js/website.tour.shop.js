(function () {
    'use strict';

    var website = openerp.website;

    website.EditorBar.include({
        start: function () {
            this.registerTour(new website.EditorShopTour(this));
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
                    stepId: 'welcome-shop',
                    title: "Welcome to your shop",
                    content: "You successfully installed the e-commerce. This guide will help you to create your product and promote your sales.",
                    template: self.popover({ next: "Start Tutorial", end: "Skip It" }),
                    backdrop: true,
                },
                {
                    stepId: 'content-menu',
                    element: '#content-menu-button',
                    placement: 'left',
                    title: "Create your first product",
                    content: "Click here to add a new product.",
                    trigger: 'click',
                },
                {
                    stepId: 'edit-entry',
                    element: '#create-new-product',
                    placement: 'left',
                    title: "Create a new product",
                    content: "Select 'New Product' to create it and manage its properties to boost your sales.",
                    trigger: {
                        modal: {
                            stopOnClose: true,
                            afterSubmit: 'product-page',
                        },
                    },
                },
                {
                    stepId: 'enter-name',
                    element: '.modal input[type=text]',
                    placement: 'right',
                    title: "Choose name",
                    content: "Enter a name for your new product then click 'Continue'.",
                },
                {
                    stepId: 'product-page',
                    title: "New product created",
                    content: "This page contains all the information related to the new product.",
                    template: self.popover({ next: "OK" }),
                    backdrop: true,
                },
                {
                    stepId: 'edit-price',
                    element: '.product_price',
                    placement: 'left',
                    title: "Change the public price",
                    content: "Edit the sale price of this product by clicking on the amount. The price is the sale price used in all sale order when selling this product.",
                    template: self.popover({ next: "OK" }),
                },
                {
                    stepId: 'update-image',
                    element: '#wrap img.img:first',
                    placement: 'top',
                    title: "Update image",
                    content: "Click here to set an image describing your product.",
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
                    stepId: 'upload-image',
                    element: 'button.filepicker',
                    placement: 'left',
                    title: "Upload image",
                    content: "Click on 'Upload an image from your computer' to pick an image describing your product.",
                    template: self.popover({ next: "OK" }),
                    triggers: function () {
                        $(document).on('hide.bs.modal', function () {
                            self.moveToStep('add-block');
                        });
                    }
                },
                {
                    stepId: 'save-image',
                    element: 'button.save',
                    placement: 'right',
                    title: "Save the image",
                    content: "Click 'Save Changes' to add the image to the product decsription.",
                },
                {
                    stepId: 'add-block',
                    element: 'button[data-action=snippet]',
                    placement: 'bottom',
                    title: "Describe the product for your audience",
                    content: "Insert blocks like text-image, or gallery to fully describe the product and make your visitors want to buy this product.",
                    trigger: {
                        emitter: editor,
                        type: 'openerp',
                        id: 'rte:ready',
                    },
                },
                {
                    stepId: 'drag-big-picture',
                    snippet: 'big-picture',
                    placement: 'bottom',
                    title: "Drag & Drop a block",
                    content: "Drag the 'Big Picture' block and drop it in your page.",
                    trigger: 'drag',
                },
                {
                    stepId: 'save-changes',
                    element: 'button[data-action=save]',
                    placement: 'right',
                    title: "Save your modifications",
                    content: "Once you click on save, your product is updated.",
                    trigger: 'click',

                },
                {
                    stepId: 'publish-product',
                    element: 'button.js_publish_btn',
                    placement: 'top',
                    title: "Publish your product",
                    content: "Click to publish your product so your customers can see it.",
                    trigger: 'click',
                },
            ];
            return this._super();
        },
        trigger: function () {
            return (this.resume() && this.testUrl(/^\/shop\/product\/[0-9]+\//)) || this._super();
        },
    });

}());
