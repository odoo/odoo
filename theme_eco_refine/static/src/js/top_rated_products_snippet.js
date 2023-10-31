odoo.define('theme_eco_refine.rated_products', function(require) {
    "use strict";
    var PublicWidget = require('web.public.widget')
    var ajax = require('web.ajax');
    var core = require('web.core')
    var Qweb = core.qweb;
    var RatedProducts = PublicWidget.Widget.extend({
        selector: '.top_rated_product_snippet',
        willStart: async function() {
            var self = this;
            await ajax.jsonRpc('/top_rated_products', 'call', {}).then(function(data) {
                self.products = data[0];
                self.categories = data[3];
                self.website_id = data[2];
            });
        },
        start: function() {
            var products = this.products;
            var categories = this.categories;
            var current_website_id = this.website_id;
            var products_list = [];
            var best_seller = [];
            $(document).ready(function () {
                $(".top_rated").owlCarousel({
                    items: 4,
                    loop: false,
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
                          loop: false,

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
                'products': best_seller
            });
            $('#top_rated_carousel').html(
                Qweb.render('theme_eco_refine.top_rated_products', {
                    products: products,
                    categories: categories,
                    current_website_id: current_website_id,
                    products_list: products_list
                })
            );
            $('.top_selling').each(function() {
                if ($(this).children().length === 0) {
                    $(this).remove();
                }
            });
            $('.top').each(function() {
                if ($(this).children().length === 0) {
                    $(this).remove();
                }
            });
        }
    });
    PublicWidget.registry.top_rated_product_snippet = RatedProducts;
    return RatedProducts;
});
