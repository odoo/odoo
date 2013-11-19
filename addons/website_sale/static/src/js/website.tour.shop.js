(function () {
    'use strict';

    var website = openerp.website;

    var render = website.tour.render;

    website.EditorShopTour = website.EditorTour.extend({
        id: 'shop-tutorial',
        name: "Create a product",
        startPath: '/shop',
        init: function (editor) {
            var self = this;
            var $body = $(document.body);
            self.steps = [
                {
                    stepId: 'welcome-shop',
                    orphan: true,
                    backdrop: true,
                    title: "Welcome to your shop",
                    content: "You successfully installed the e-commerce. This guide will help you to create your product and promote your sales.",
                    template: render('website.tour_popover', { next: "Start Tutorial", end: "Skip It" }),
                },
                {
                    stepId: 'content-menu',
                    element: '#content-menu-button',
                    placement: 'left',
                    reflex: true,
                    title: "Create your first product",
                    content: "Click here to add a new product.",
                    template: render('website.tour_popover'),
                },
                {
                    stepId: 'edit-entry',
                    element: '#create-new-product',
                    placement: 'left',
                    title: "Create a new product",
                    content: "Select 'New Product' to create it and manage its properties to boost your sales.",
                    template: render('website.tour_popover'),
                    onShow: function () {
                        $(document).one('shown.bs.modal', function () {
                            $('.modal button.btn-primary').click(function () {
                                self.movetoStep('product-page');
                            });
                            self.movetoStep('enter-name');
                        });
                    },
                },
                {
                    stepId: 'enter-name',
                    element: '.modal input[type=text]',
                    placement: 'right',
                    title: "Choose name",
                    content: "Enter a name for your new product.",
                    template: render('website.tour_popover'),

                },
                {
                    stepId: 'product-page',
                    orphan: true,
                    backdrop: true,
                    title: "New product created",
                    content: "This page contains all the information related to the new product.",
                    template: render('website.tour_popover', { next: "OK" }),
                },
                {
                    stepId: 'edit-price',
                    element: '.product_price',
                    placement: 'left',
                    title: "Change the public price",
                    content: "Edit the sale price of this product by clicking on the amount. The price is the sale price used in all sale order when selling this product.",
                    template: render('website.tour_popover', { next: "OK" }),
                },
                {
                    stepId: 'add-block',
                    element: 'button[data-action=snippet]',
                    placement: 'bottom',
                    reflex: true,
                    title: "Describe the product for your audience",
                    content: "Insert blocks like text-image, or gallery to fully describe the product and make your visitors want to buy this product.",
                    template: render('website.tour_popover'),
                },
            ];
            return this._super();
        },
        productPage: function () {
            var currentStepIndex = this.currentStepIndex();
            var productPageIndex = this.indexOfStep('product-page');
            return (currentStepIndex === productPageIndex) && !this.tour.ended();
        },
        continueTour: function () {
            return this.productPage();
        },
        isTriggerUrl: function (url) {
            url = url || new website.UrlParser(window.location.href);
            var addProductPattern = /^\/shop\/product\/[0-9]+\/\?enable_editor=1/;
            return addProductPattern.test(url.pathname+url.search) || this._super();
        },
    });

    website.EditorBar.include({
        start: function () {
            this.registerTour(new website.EditorShopTour(this));
            return this._super();
        },
    });

}());
