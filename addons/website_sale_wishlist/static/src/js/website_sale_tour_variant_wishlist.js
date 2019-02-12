odoo.define('website_sale_wishlist.tour_shop_variant', function (require) {
'use strict';

var tour = require('web_tour.tour');
var base = require('web_editor.base');
var rpc = require('web.rpc');
var session = require('web.session');

tour.register('shop_variant_wishlist', {
        url: "/",
        wait_for: base.ready(),
    }, [
    {
        content: "create product with newly created attribute and its value",
        trigger: '#wrapwrap',
        run: function () {
            rpc.query({
                model: 'product.attribute',
                method: 'create',
                args: [{
                    'name': 'color',
                    'type': 'color',
                    'create_variant': 'dynamic'
                }],
            }).then(function (attribute_id) {
                rpc.query({
                model: 'product.template',
                method: 'create',
                args: [{
                    'name': 'Bottle',
                    'is_published': true,
                    'attribute_line_ids': [[0, 0 , {
                        'attribute_id': attribute_id,
                        'value_ids': [[0, 0, {
                                'name': 'red',
                                'attribute_id': attribute_id,
                            }],
                            [0, 0, {
                                'name': 'blue',
                                'attribute_id': attribute_id,
                            }],
                            [0, 0, {
                                'name': 'black',
                                'attribute_id': attribute_id,
                            }],
                            ]
                        }]]
                    }],
                })
            }).then(function () {
                window.location.href = '/web/session/logout';
            });
        },
    },
    {
        content: "Search product 'Bottle'",
        extra_trigger: '#wrapwrap .oe_website_login_container',
        trigger: '#wrapwrap',
        run: function() {
            window.location.href = '/shop?search=Bottle';
        },
    },
    {
        content: "Add Bottle to wishlist from /shop",
        extra_trigger: '.oe_product_cart:contains("Bottle")',
        trigger: '.oe_product_cart:contains("Bottle") .o_add_wishlist',
    },
    {
        content: "check that wishlist contains 1 item",
        trigger: '.my_wish_quantity:contains(1)',
    },
    {
        content: "Click on product",
        trigger: '.oe_product_cart a:contains("Bottle")',
    },
    {
        content: "Select Bottle with second variant from /product",
        trigger: '.variant_attribute li input[data-value_name="blue"]',
    },
    {
        content: "Add product in wishlist",
        extra_trigger: '#product_detail .o_add_wishlist_dyn:not(".disabled")',
        trigger: '#product_detail .o_add_wishlist_dyn',
    },
    {
        content: "Select Bottle with third variant from /product",
        trigger: '.variant_attribute li input[data-value_name="black"]',
    },
    {
        content: "Add product in wishlist",
        extra_trigger: '#product_detail .o_add_wishlist_dyn:not(".disabled")',
        trigger: '#product_detail .o_add_wishlist_dyn',
    },
    {
        content: "check that wishlist contains 3 item",
        trigger: '.my_wish_quantity:contains(3)',
    },
    {
        content: "See wishlist products",
        trigger: 'a[href="/shop/wishlist"]:visible',
    },
    {
        content: "Wishlist contains first variant product",
        trigger: '#o_comparelist_table tr:contains("red")',
    },
    {
        content: "Wishlist contains second variant product",
        trigger: '#o_comparelist_table tr:contains("blue")',
    },
    {
        content: "Wishlist contains third variant product",
        trigger: '#o_comparelist_table tr:contains("black")',
    },
    {
        content: "Sign in as admin",
        extra_trigger: '.my_wish_quantity:contains(3)',
        trigger: 'a[href="/web/login"]',
    },
    {
        content: "submit login",
        trigger: '.oe_login_form',
        run: function (){
            $('.oe_login_form input[name="login"]').val("admin");
            $('.oe_login_form input[name="password"]').val("admin");
            $('.oe_login_form input[name="redirect"]').val("/shop");
            $('.oe_login_form').submit();
        },
    },
    // test an impossible combination (with archive only one variant)
    {
        content: "Archive variants",
        extra_trigger: '.js_sale',
        trigger: '.js_sale',
        run: function () {
            rpc.query({
                model: 'product.product',
                method: 'search',
                args: [[['name', '=', "Bottle"]]],
            })
            .then(function (product_ids) {
                return rpc.query({
                    model: 'product.product',
                    method: 'write',
                    args: [product_ids[0], {active: false}],
                });
            })
            .then(function () {
                window.location.href = '/web/session/logout';
            });
        },
    },
    {
        content: "Search product 'Bottle'",
        extra_trigger: '#top_menu li a:contains("Sign in")',
        trigger: '#wrapwrap',
        run: function() {
            window.location.href = '/shop?search=Bottle';
        },
    },
    {
        content: "Check that there is wishlist button on product from /shop",
        extra_trigger: '.js_sale',
        trigger: '.oe_product_cart:contains("Bottle") .o_add_wishlist',
    },
    {
        content: "Click on product",
        trigger: '.oe_product_cart a:contains("Bottle")',
    },
    {
        content: "Select Bottle with first(red) variant from /product",
        trigger: '.variant_attribute li input[data-value_name="red"]',
    },
    {
        content: "check that there is no wishlist button on selecting first variant",
        trigger: '#product_detail:not(:has(.o_add_wishlist))',
    },
    {
        content: "Select Bottle with second(blue) variant from /product",
        trigger: '.variant_attribute li input[data-value_name="blue"]',
    },
    {
        content: "Check that wishlist button is there when selecting other variants from /product",
        trigger: '#product_detail .o_add_wishlist_dyn',
    },
    {
        content: "Sign in as admin",
        extra_trigger: '.my_wish_quantity:contains(1)',
        trigger: 'a[href="/web/login"]',
    },
    {
        content: "submit login",
        trigger: '.oe_login_form',
        run: function (){
            $('.oe_login_form input[name="login"]').val("admin");
            $('.oe_login_form input[name="password"]').val("admin");
            $('.oe_login_form input[name="redirect"]').val("/shop");
            $('.oe_login_form').submit();
        },
    },
    // test an impossible combination (with archive all variants)
    {
        content: "Archive variants",
        extra_trigger: '.js_sale',
        trigger: '.js_sale',
        run: function () {
            rpc.query({
                model: 'product.product',
                method: 'search',
                args: [[['name', '=', "Bottle"]]],
            })
            .then(function (product_ids) {
                return rpc.query({
                    model: 'product.product',
                    method: 'write',
                    args: [product_ids, {active: false}],
                })
            })
            .then(function () {
                window.location.href = '/web/session/logout';
            });
        }
    },
    {
        content: "Search product 'Bottle'",
        extra_trigger: '#top_menu li a:contains("Sign in")',
        trigger: '#wrapwrap',
        run: function() {
            window.location.href = '/shop?search=Bottle';
        },
    },
    {
        content: "Check that there is no wishlist button from /shop",
        extra_trigger: '.js_sale',
        trigger: '.oe_product_cart:contains("Bottle"):not(:has(.o_add_wishlist))',
    },
    {
        content: "Click on product",
        trigger: '.oe_product_cart a:contains("Bottle")',
    },
    {
        content: "Check that there is no wishlist button from /product",
        trigger: '#product_detail:not(:has(.o_add_wishlist_dyn))',
    },
    ]);
});
