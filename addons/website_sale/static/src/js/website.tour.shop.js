(function () {
    'use strict';

    var website = openerp.website;

    var render = website.tour.render;

    website.EditorShopTour = website.EditorTour.extend({
        id: 'shop_tour',
        name: "Create a product",
        urlTrigger: '?shop-tutorial=true',
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
            ];
            return this._super();
        },
        redirect: function (url) {
            url = url || new website.UrlParser(window.location.href);
            if (url.pathname !== '/shop') {
                window.location.replace('/shop?shop-tutorial=true');
            }
        },
    });

    website.EditorBar.include({
        start: function () {
            this.registerTour(new website.EditorShopTour(this));
            return this._super();
        },
    });

}());
