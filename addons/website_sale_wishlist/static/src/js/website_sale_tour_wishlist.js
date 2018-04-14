odoo.define('website_sale_wishlist.tour', function (require) {
'use strict';

var tour = require("web_tour.tour");
var base = require("web_editor.base");

tour.register('shop_wishlist', {
    test: true,
    url: '/shop',
    wait_for: base.ready(),
},
    [
        {
            content: "click on add to wishlist",
            trigger: '.o_add_wishlist',
        },
        {
            content: "go to wishlist",
            extra_trigger: ".label:contains(1)",
            trigger: 'a[href="/shop/wishlist"]',
        },
        {
            content: "remove first item in whishlist",
            trigger: 'a.o_wish_rm:first',
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
                $('.oe_login_form input[name="redirect"]').val("/shop");
                $('.oe_login_form').submit();
            },
        },
        {
            content: "check that logged in and search for ipad",
            extra_trigger: 'li span:contains(Administrator)',
            trigger: 'form input[name="search"]',
            run: "text ipad retina",
        },
        {
            content: "submit search",
            trigger: 'form:has(input[name="search"]) .oe_search_button',
        },
        {
            content: "click on ipad",
            trigger: '.oe_product_cart a:contains("iPad Retina Display")',
        },
        {
            content: "select ipad 32GB",
            extra_trigger: '#product_detail',
            trigger: 'label:contains(32 GB) input',
        },
        {
            content: "click on add to wishlist",
            trigger: '#product_detail .o_add_wishlist_dyn',
        },
        {
            content: "check that wishlist contains 2 items and go to wishlist",
            extra_trigger: ".label:contains(2)",
            trigger: 'a[href="/shop/wishlist"]',
        },
        {
            content: "remove Ipad",
            trigger: 'tr:contains("iPad Retina Display") a.o_wish_rm:first',
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
            trigger: 'a.o_wish_add:first',
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
            trigger: 'a.o_wish_add:first',
        },
        {
            content: "check that user is redirect - wishlist is empty",
            trigger: "h2:contains('Shopping Cart')",
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
    ]
);

});
