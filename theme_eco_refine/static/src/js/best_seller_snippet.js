odoo.define('theme_eco_refine.top_selling_products', function (require) {
    "use strict";
    var PublicWidget = require('web.public.widget');
    var ajax = require('web.ajax');
    var core = require('web.core');
    var Qweb = core.qweb;
    var TopSellingProducts = PublicWidget.Widget.extend({
        selector: '.best_seller_product_snippet',
        willStart: async function () {
            var self = this;
            await ajax.jsonRpc('/top_selling_products', 'call', {}).then(function (data) {
                self.products = data[0];
                self.categories = data[1];
                self.website_id = data[2];
                self.unique_id = data[3];
            });
        },
        start: function () {
            var self = this;
            var products = this.products;
            var categories = this.categories;
            var current_website_id = this.website_id;
            var unique_id = this.unique_id;
            var products_list = [];
            var best_seller = [];
            $(document).ready(function () {
                $(".top_selling").owlCarousel({
                    items: 4,
                    loop: true,
                    margin: 20,
                    stagePadding: 0,
                    smartSpeed: 450,
                    autoplay: false,
                    autoPlaySpeed: 3000,
                    autoPlayTimeout: 1000,
                    autoplayHoverPause: true,
                    dots: false,
                    responsive: {
                        0: {
                          items: 1,
                          nav: true
                        },
                        400: {
                          items: 2,
                          nav: false
                        },
                        1000: {
                          items: 4,
                          nav: true,
                          loop: true,
                          margin: 0
                      }
                    },
                    nav: true,
                    navText: [
                        "<img src='/website_customisation/static/src/img/caret-back.png'>",
                        "<img src='/website_customisation/static/src/img/caret-forward.png'>",
                    ],
                });
            });
            for (var i = 0; i < products.length; i += 4) {
                best_seller.push(products.slice(i, i + 4));
            }
            if (best_seller.length > 1) {
                best_seller[0].is_active = true;
                best_seller.push('chunk');
            }
            products_list.push({
                'category': categories[0],
                'products': best_seller,
                'unique_id':unique_id,
            });
            self.$('#top_products_carousel').html(
                Qweb.render('theme_eco_refine.products_category_wise', {
                    products: products,
                    categories: categories,
                    current_website_id: current_website_id,
                    products_list: products_list
                })
            );
            self.$('.top_selling').each(function () {
                if (self.$(this).children().length === 0) {
                    self.$(this).remove();
                }
            });
            self.$('.top').each(function () {
                if (self.$(this).children().length === 0) {
                    self.$(this).remove();
                }
            });
        }
    });
    PublicWidget.registry.products_category_wise_snippet = TopSellingProducts;
    return TopSellingProducts;
});
