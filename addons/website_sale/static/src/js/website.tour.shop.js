(function () {
    'use strict';

    var website = openerp.website;

    var render = website.tour.render;

    website.EditorShopTour = website.EditorTour.extend({
        id: 'shop_tour',
        name: "Create a product",
        init: function (editor) {
            var self = this;
            var $body = $(document.body);
            self.steps = [
                {
                    stepId: 'welcome-shop',
                    orphan: true,
                    backdrop: true,
                    title: "e-commerce",
                    content: "Welcome to the e-commerce. This tutorial will help you to create a product.",
                    template: render('website.tour_popover', { next: "Start Tutorial", end: "Skip It" }),
                },
            ];
            return this._super();
        },
    });

    website.EditorBar.include({
        start: function () {
            var menu = $('#help-menu');
            var shopTour = new website.EditorShopTour(this);
            var $menuItem = $($.parseHTML('<li><a href="#">'+shopTour.name+'</a></li>'));
            var url = new website.UrlParser(window.location.href);
            $menuItem.click(function () {
                shopTour.reset();
                shopTour.start();
                if (url.pathname !== '/shop') {
                    window.location.replace('/shop?shop-tutorial=true');
                }
            });
            if (url.search.indexOf('?shop-tutorial=true') === 0) {
                shopTour.start();
            }
            menu.append($menuItem);
            return this._super();
        },
    });

}());
