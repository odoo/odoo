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
        id: 'shop-tutorial',
        name: "Create a product",
        init: function (editor) {
            var self = this;
            self.steps = [
                {
                    stepId: 'welcome-shop',
                    orphan: true,
                    backdrop: true,
                    title: "Welcome to your shop",
                    content: "You successfully installed the e-commerce. This guide will help you to create your product and promote your sales.",
                    template: self.popover({ next: "Start Tutorial", end: "Skip It" }),
                },
                {
                    stepId: 'content-menu',
                    element: '#content-menu-button',
                    placement: 'left',
                    reflex: true,
                    title: "Create your first product",
                    content: "Click here to add a new product.",
                },
                {
                    stepId: 'edit-entry',
                    element: '#create-new-product',
                    placement: 'left',
                    title: "Create a new product",
                    content: "Select 'New Product' to create it and manage its properties to boost your sales.",
                    triggers: function () {
                        $(document).one('shown.bs.modal', function () {
                            $('.modal button.btn-primary').one('click', function () {
                                self.moveToStep('product-page');
                            });
                            self.moveToNextStep();
                        });
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
                    orphan: true,
                    backdrop: true,
                    title: "New product created",
                    content: "This page contains all the information related to the new product.",
                    template: self.popover({ next: "OK" }),
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
                            $('button.image-edit-button').one('click', function () {
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
                },
                {
                    stepId: 'save-image',
                    element: 'button.save',
                    placement: 'right',
                    reflex: true,
                    title: "Save the image",
                    content: "Click 'Save Changes' to add the image to the product decsription.",
                },
                {
                    stepId: 'add-block',
                    element: 'button[data-action=snippet]',
                    placement: 'bottom',
                    title: "Describe the product for your audience",
                    content: "Insert blocks like text-image, or gallery to fully describe the product and make your visitors want to buy this product.",
                    triggers: function () {
                        $('button[data-action=snippet]').one('click', function () {
                            self.moveToNextStep();
                        });
                    },
                },
                {
                    stepId: 'drag-big-picture',
                    element: '#website-top-navbar [data-snippet-id=big-picture].ui-draggable',
                    placement: 'bottom',
                    title: "Drag & Drop a block",
                    content: "Drag the 'Big Picture' block and drop it in your page.",
                    triggers: function () {
                        self.onSnippetDraggedAdvance('big-picture');
                    },
                },
                {
                    stepId: 'publish-post',
                    element: 'button.js_publish_btn',
                    placement: 'right',
                    reflex: true,
                    title: "Publish your product",
                    content: "Click to publish your product so your customers can see it.",
                },
                {
                    stepId: 'save-changes',
                    element: 'button[data-action=save]',
                    placement: 'right',
                    reflex: true,
                    title: "Save your modifications",
                    content: "Once you click on save, your product is updated.",
                },
            ];
            return this._super();
        },
        resume: function () {
            return this.isCurrentStep('product-page') && !this.tour.ended();
        },
        trigger: function (url) {
            return (this.resume() && this.testUrl(/^\/shop\/product\/[0-9]+\/\?enable_editor=1/)) || this._super();
        },
    });

}());
