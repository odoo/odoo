odoo.define('website_sale_wishlist.tour', function (require) {
'use strict';

var rpc = require('web.rpc');
var tour = require("web_tour.tour");

tour.register('shop_wishlist', {
    test: true,
    url: '/shop?search=Customizable Desk',
},
    [
        {
            content: "click on add to wishlist",
            trigger: '.o_add_wishlist',
        },
        {
            content: "go to wishlist",
            extra_trigger: 'a[href="/shop/wishlist"] .badge:contains(1)',
            trigger: 'a[href="/shop/wishlist"]',
        },
        {
            content: "remove first item in whishlist",
            trigger: '.o_wish_rm:first',
        },
        {
            content: "go back to the store",
            trigger: "a[href='/shop']"
        },
        {
            content: "click on add to wishlist",
            trigger: '.o_add_wishlist',
        },
        {
            content: "check value of wishlist and go to login",
            extra_trigger: ".my_wish_quantity:contains(1)",
            trigger: 'a[href="/web/login"]',
        },
        {
            content: "submit login",
            trigger: ".oe_login_form",
            run: function (){
                $('.oe_login_form input[name="login"]').val("admin");
                $('.oe_login_form input[name="password"]').val("admin");
                $('.oe_login_form input[name="redirect"]').val("/shop?search=Customizable Desk");
                $('.oe_login_form').submit();
            },
        },
        {
            content: "check that logged in",
            trigger: "li span:contains('Mitchell Admin')",
            run: function () {},
        },
        {
            content: "click on Customizable Desk (TEST)",
            trigger: '.oe_product_cart a:contains("Customizable Desk")',
        },
        {
            content: "check the first variant is already in wishlist",
            trigger: '#product_detail .o_add_wishlist_dyn:disabled',
            run: function () {},
        },
        {
            content: "change variant",
            extra_trigger: '#product_detail label:contains(Aluminium) input',
            trigger: 'label:contains(Aluminium) input',
        },
        {
            content: "wait button enable and click on add to wishlist",
            extra_trigger: '#product_detail .o_add_wishlist_dyn:not(:disabled)',
            trigger: '#product_detail .o_add_wishlist_dyn',
        },
        {
            content: "check that wishlist contains 2 items and go to wishlist",
            extra_trigger: 'a[href="/shop/wishlist"] .badge:contains(2)',
            trigger: 'a[href="/shop/wishlist"]',
        },
        {
            content: "remove Customizable Desk (TEST)",
            trigger: 'tr:contains("Customizable Desk") .o_wish_rm:first',
        },
        {
            content: "check that wishlist contains 1 item",
            trigger: ".my_wish_quantity:contains(1)",
            run: function() {},
        },
        {
            content: "check B2B wishlist mode",
            trigger: "input#b2b_wish",
        },
        {
            content: "add item to cart",
            trigger: '.o_wish_add:eq(1)',
        },
        {
            content: "check that cart contains 1 item",
            trigger: ".my_cart_quantity:contains(1)",
            run: function() {},
        },
        {
            content: "check that wishlist contains 1 item",
            trigger: ".my_wish_quantity:contains(1)",
            run: function() {},
        },
        {
            content: "remove B2B wishlist mode",
            trigger: "input#b2b_wish",
        },
        {
            content: "add last item to cart",
            trigger: '.o_wish_add:eq(1)',
        },
        {
            content: "check that user is redirect - wishlist is empty",
            trigger: "#wrap #cart_products",
            run: function() {},
        },
        {
            content: "check that cart contains 2 items",
            trigger: ".my_cart_quantity:contains(2)",
            run: function() {},
        },
        {
            content: "check that wishlist is empty and no more visible",
            trigger: ":not(:has(.my_wish_quantity:visible))",
            run: function() {},
        },
        // Test dynamic attributes
        {
            content: "Create a product with dynamic attribute and its values.",
            trigger: 'body',
            run: function () {
                rpc.query({
                    model: 'product.attribute',
                    method: 'create',
                    args: [{
                        'name': "color",
                        'display_type': 'color',
                        'create_variant': 'dynamic'
                    }],
                }).then(function (attributeId) {
                    return rpc.query({
                        model: 'product.template',
                        method: 'create',
                        args: [{
                            'name': "Bottle",
                            'is_published': true,
                            'attribute_line_ids': [[0, 0, {
                                'attribute_id': attributeId,
                                'value_ids': [
                                    [0, 0, {
                                        'name': "red",
                                        'attribute_id': attributeId,
                                    }],
                                    [0, 0, {
                                        'name': "blue",
                                        'attribute_id': attributeId,
                                    }],
                                    [0, 0, {
                                        'name': "black",
                                        'attribute_id': attributeId,
                                    }],
                                ]
                            }]],
                        }],
                    });
                }).then(function () {
                    window.location.href = '/web/session/logout?redirect=/shop?search=Bottle';
                });
            },
        },
        {
            content: "Add Bottle to wishlist from /shop",
            extra_trigger: '.oe_product_cart:contains("Bottle")',
            trigger: '.oe_product_cart:contains("Bottle") .o_add_wishlist',
        },
        {
            content: "Check that wishlist contains 1 item",
            trigger: '.my_wish_quantity:contains(1)',
            run: function () {},
        },
        {
            content: "Click on product",
            extra_trigger: '.oe_product_cart:contains("Bottle") .o_add_wishlist.disabled',
            trigger: '.oe_product_cart a:contains("Bottle")',
        },
        {
            content: "Select Bottle with second variant from /product",
            trigger: '.js_variant_change[data-value_name="blue"]',
        },
        {
            content: "Add product in wishlist",
            extra_trigger: '#product_detail .o_add_wishlist_dyn:not(".disabled")',
            trigger: '#product_detail .o_add_wishlist_dyn',
        },
        {
            content: "Select Bottle with third variant from /product",
            trigger: '.js_variant_change[data-value_name="black"]',
        },
        {
            content: "Add product in wishlist",
            extra_trigger: '#product_detail .o_add_wishlist_dyn:not(".disabled")',
            trigger: '#product_detail .o_add_wishlist_dyn',
        },
        {
            content: "Check that wishlist contains 3 items and go to wishlist",
            trigger: '.my_wish_quantity:contains(3)',
            run: function () {
                window.location.href = '/shop/wishlist';
            },
        },
        {
            content: "Check wishlist contains first variant",
            trigger: '#o_comparelist_table tr:contains("red")',
            run: function () {},
        },
        {
            content: "Check wishlist contains second variant",
            trigger: '#o_comparelist_table tr:contains("blue")',
            run: function () {},
        },
        {
            content: "Check wishlist contains third variant, then go to login",
            trigger: '#o_comparelist_table tr:contains("black")',
            run: function () {
                window.location.href = "/web/login";
            },
        },
        {
            content: "Submit login as admin",
            trigger: '.oe_login_form',
            run: function () {
                $('.oe_login_form input[name="login"]').val("admin");
                $('.oe_login_form input[name="password"]').val("admin");
                $('.oe_login_form input[name="redirect"]').val("/");
                $('.oe_login_form').submit();
            },
        },
        // Test one impossible combination while other combinations are possible
        {
            content: "Archive the first variant",
            trigger: '#top_menu:contains("Mitchell Admin")',
            run: function () {
                rpc.query({
                    model: 'product.product',
                    method: 'search',
                    args: [[['name', '=', "Bottle"]]],
                })
                .then(function (productIds) {
                    return rpc.query({
                        model: 'product.product',
                        method: 'write',
                        args: [productIds[0], {active: false}],
                    });
                })
                .then(function () {
                    window.location.href = '/web/session/logout?redirect=/shop?search=Bottle';
                });
            },
        },
        {
            content: "Check there is wishlist button on product from /shop",
            extra_trigger: '.js_sale',
            trigger: '.oe_product_cart:contains("Bottle") .o_add_wishlist',
            run: function () {},
        },
        {
            content: "Click on product",
            trigger: '.oe_product_cart a:contains("Bottle")',
        },
        {
            content: "Select Bottle with first variant (red) from /product",
            trigger: '.js_variant_change[data-value_name="red"]',
        },
        {
            content: "Check there is no wishlist button when selecting impossible variant",
            trigger: '#product_detail:not(:has(.o_add_wishlist))',
            run: function () {},
        },
        {
            content: "Select Bottle with second variant (blue) from /product",
            trigger: '.js_variant_change[data-value_name="blue"]',
        },
        {
            content: "Click on wishlist when selecting a possible variant from /product",
            trigger: '#product_detail .o_add_wishlist_dyn:not(.disabled)',
        },
        {
            content: "Check product added to wishlist and go to login",
            trigger: '.my_wish_quantity:contains(1)',
            run: function () {
                window.location.href = "/web/login";
            },
        },
        {
            content: "Submit login",
            trigger: '.oe_login_form',
            run: function () {
                $('.oe_login_form input[name="login"]').val("admin");
                $('.oe_login_form input[name="password"]').val("admin");
                $('.oe_login_form input[name="redirect"]').val("/");
                $('.oe_login_form').submit();
            },
        },
        // test when all combinations are impossible
        {
            content: "Archive all variants",
            trigger: '#top_menu:contains("Mitchell Admin")',
            run: function () {
                rpc.query({
                    model: 'product.product',
                    method: 'search',
                    args: [[['name', '=', "Bottle"]]],
                })
                .then(function (productIds) {
                    return rpc.query({
                        model: 'product.product',
                        method: 'write',
                        args: [productIds, {active: false}],
                    });
                })
                .then(function () {
                    window.location.href = '/web/session/logout?redirect=/shop?search=Bottle';
                });
            }
        },
        {
            content: "Check that there is no wishlist button from /shop",
            extra_trigger: '.js_sale',
            trigger: '.oe_product_cart:contains("Bottle"):not(:has(.o_add_wishlist))',
            run: function () {},
        },
        {
            content: "Click on product",
            trigger: '.oe_product_cart a:contains("Bottle")',
        },
        {
            content: "Check that there is no wishlist button from /product",
            trigger: '#product_detail:not(:has(.o_add_wishlist_dyn))',
            run: function () {},
        },
        // Test if the wishlist button is active or not in /shop
        {
            content: "Go to '/shop?search=Customizable Desk'",
            trigger: 'body',
            run: function () {
                window.location.href = '/shop?search=Customizable Desk '
            },
        },
        {
            content: "Click on the product",
            trigger: '.oe_product_image_link img',
        },
        {
            content: "Add the product in the wishlist",
            trigger: '#product_option_block .o_add_wishlist_dyn',
        },
        {
            content: "Added into the wishlist",
            trigger: '.my_wish_quantity.text-bg-primary:contains(1)',
            run: function () {},
        },
        {
            content: "Go to '/shop",
            trigger: '#top_menu_collapse a[href="/shop"]',
        },
        {
            content: "Search the product Customizable Desk'",
            trigger: 'form.o_wsale_products_searchbar_form input',
            run: function () {
                $('form.o_wsale_products_searchbar_form input[name="search"]').val("Customizable Desk");
                $('form.o_wsale_products_searchbar_form button').click();
            },
        },
        {
            content: "The product is in the wishlist",
            trigger: '.oe_product_cart .o_wsale_product_information:has(.o_add_wishlist[disabled])',
            run: function () {},
        },
        {
            content: "Go to the wishlist",
            trigger: 'a[href="/shop/wishlist"]',
        },
        {
            content: "Remove the product from the wishlist",
            trigger: '.o_wish_rm',
        },
        {
            content: "Go to '/shop",
            trigger: '#top_menu_collapse a[href="/shop"]',
        },
        {
            content: "Search the product Customizable Desk'",
            trigger: 'form.o_wsale_products_searchbar_form input',
            run: function () {
                $('form.o_wsale_products_searchbar_form input[name="search"]').val("Customizable Desk");
                $('form.o_wsale_products_searchbar_form button').click();
            },
        },
        {
            content: "The product is not in the wishlist",
            trigger: '.oe_product_cart .o_wsale_product_information:not(:has(.o_add_wishlist[disabled]))',
            run: function () {},
        },
    ]
);

});
