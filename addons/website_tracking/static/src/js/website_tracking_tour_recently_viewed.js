odoo.define('website_tracking.tour', function (require) {
'use strict';

var tour = require("web_tour.tour");
var utils = require('web.utils');

var doAtShop1 = {
    content: "snippet is in /shop and add product to cart",
    extra_trigger: 'section.s_wtracking_products_recently_viewed',
    trigger: '.slider div.o-product-card:has(input[data-product-id="27"]) button.js_add_cart',
};
var doAtShop2 = {
    content: "Shop nav bar updated",
    extra_trigger: 'li#my_cart sup.my_cart_quantity:contains(1)',
    trigger: '.slider:not(:has(div.o-product-card:has(input[data-product-id="27"])))',
    run: function () {
        window.location.href = window.location.origin + '/shop/product/customizable-desk-9';
    },
};
var doAtProduct1 = {
    content: '"snippet is in /products and product on page not in snippet',
    extra_trigger: 'section.s_wtracking_products_recently_viewed',
    trigger: '.slider:not(:has(div.o-product-card:has(input[data-product-id="10"]))):not(:has(div.o-product-card:has(input[data-product-id="27"]))):has(div.o-product-card:has(input[data-product-id="7"]))',
    run: function () {
        window.location.href = window.location.origin + '/shop/cart';
    },
};
var doAtCart1 = {
    content: "snippet is in /cart and cart updated",
    extra_trigger: 'section.s_wtracking_products_recently_viewed',
    trigger: '#cart_products:has(input.js_quantity[data-product-id="27"])',
};
var doAtCart2 = {
    content: "Cart nav bar updated and add product to cart",
    trigger: '.slider div.o-product-card:has(input[data-product-id="7"]) button.js_add_cart',
};
var doAtCart3 = {
    content: "Cart updated",
    extra_trigger: '.slider:not(:has(div.o-product-card:has(input[data-product-id="27"]))):not(:has(div.o-product-card:has(input[data-product-id="7"]))):has(div.o-product-card:has(input[data-product-id="10"]))',
    trigger: '#cart_products:has(input.js_quantity[data-product-id="7"]):has(input.js_quantity[data-product-id="27"])',
};
var doAtCart4 = {
    content: "Cart nav bar updated and add product to cart",
    trigger: 'li#my_cart sup.my_cart_quantity:contains(2)',
};

tour.register('recently_viewed', {
    test: true,
    url: '/',
},
    [
        // As a logged in User
        {
            content: 'Register a product view',
            trigger: '.oe_empty',
            run: function () {
                // TODO when rde branch is on master we will be able to register one while visiting the product page
                window.location.href = window.location.origin + '/shop';
            }
        },
        {
            content: "Shop open customize menu",
            extra_trigger: '#products_grid',
            trigger: '#customize-menu > a',
        }, {
            content: "Shop enable 'Recently Viewed Products' if needed",
            trigger: '#customize-menu a:contains(Recently Viewed Products)',
            run: function () {
                if (!$('#customize-menu a:contains(Recently Viewed Products) input').prop('checked')) {
                    $('#customize-menu a:contains(Recently Viewed Products)').click();
                }
            },
        },
        doAtShop1,
        doAtShop2,
        {
            content: "Product open customize menu",
            extra_trigger: '#product_detail',
            trigger: '#customize-menu > a',
        }, {
            content: "Product enable 'Recently Viewed Products' if needed",
            trigger: '#customize-menu a:contains(Recently Viewed Products)',
            run: function () {
                if (!$('#customize-menu a:contains(Recently Viewed Products) input').prop('checked')) {
                    $('#customize-menu a:contains(Recently Viewed Products)').click();
                }
            },
        },
        doAtProduct1,
        {
            content: "Cart open customize menu",
            extra_trigger: '.oe_cart',
            trigger: '#customize-menu > a',
        }, {
            content: "Cart enable 'Recently Viewed Products' if needed",
            trigger: '#customize-menu a:contains(Recently Viewed Products)',
            run: function () {
                if (!$('#customize-menu a:contains(Recently Viewed Products) input').prop('checked')) {
                    $('#customize-menu a:contains(Recently Viewed Products)').click();
                }
            },
        },
        doAtCart1,
        doAtCart2,
        doAtCart3,
        doAtCart4,
        // User not logged in
        {
            content: "Open Logout dropdown",
            trigger: 'a.nav-link:has(span:contains(Mitchell Admin))',
        },
        {
            content: "Logout",
            trigger: 'a#o_logout',
        },
        {
            content: "Register 3 product views as cookie",
            trigger: '.oe_empty',
            run: function () {
                // TODO when rde branch is on master we will be able to register one while visiting the product page
                utils.set_cookie('recently_viewed_product_ids', JSON.stringify([
                    [9, 10],
                    [22, 27],
                    [7, 7]
                ]));
                window.location.href = window.location.origin + '/shop';
            },
        }, {
            content: "We are on shop",
            trigger: '#products_grid',
        },
        doAtShop1,
        doAtShop2,
        doAtProduct1,
        doAtCart1,
        doAtCart2,
        doAtCart3,
        doAtCart4,
        {
            content: "Sign In",
            trigger: 'a:has(b:contains(Sign in))',
        }, {
            content: "Create Account 1",
            trigger: 'a:contains(Don\'t have an account?)',
        }, {
            content: "Create Account 2",
            trigger: 'div.field-confirm_password',
            run: function () {
                if (utils.get_cookie('recently_viewed_product_ids') === "") {
                    tour._consume_tour(tour.running_tour, 'Where is the cookie ?');
                }
                $('input#login').val('TestLogin');
                $('input#name').val('TestName');
                $('input#password').val('TestPassword');
                $('input#confirm_password').val('TestPassword');
                $('button[type="submit"]').click();
            },
        }, {
            content: "Cookies are gone",
            trigger: '.oe_empty',
            run: function () {
                if (utils.get_cookie('recently_viewed_product_ids') !== "") {
                    tour._consume_tour(tour.running_tour, 'The cookie is still here after creating an account !');
                }
            },
        }
    ]
);
});
