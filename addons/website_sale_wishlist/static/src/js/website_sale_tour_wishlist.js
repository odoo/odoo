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
            content: "check value of wishlist",
            extra_trigger: ".my_wish_quantity:contains(1)",
            trigger: ".my_wish_quantity",
        },
        {
            content: "click on login",
            trigger: 'a[href="/web/login"]',
        },
        {
            content: "login Email",
            trigger: 'form input[name="login"]',
            run: "text admin"
        },
        {
            content: "click on login",
            trigger: "body",
            run: function (actions){
                $('.oe_login_form input[name="redirect"]').val("/shop");
            },
        },
        {
            content: "login password",
            trigger: 'form input[name="password"]',
            run: "text admin"
        },
        {
            content: "login admin",
            trigger: 'form:has(input[name="login"]) .btn-primary',
        },
        {
            content: "search ipad",
            trigger: 'form input[name="search"]',
            run: "text ipad retina",
        },
        {
            content: "search ipad retina",
            trigger: 'form:has(input[name="search"]) .oe_search_button',
        },
        {
            content: "select ipad",
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
            content: "go to wishlist",
            extra_trigger: ".label:contains(2)",
            trigger: 'a[href="/shop/wishlist"]',
        },
        {
            content: "remove Ipad",
            trigger: 'tr:contains("iPad Retina Display") a.o_wish_rm:first',
        },
        {
            content: "check value of wishlist",
            extra_trigger: ".my_wish_quantity:contains(1)",
            trigger: ".my_wish_quantity",
        },
        {
            content: "check B2B add cart",
            trigger: "label:contains(Add product to my cart but keep it in my wishlist) input",
        },        
        {
            content: "add item to cart",
            trigger: 'a.o_wish_add:first',
        },
        {
            content: "check value of cart",
            extra_trigger: ".my_cart_quantity:contains(1)",
            trigger: ".my_cart_quantity",
        },
        {
            content: "check value of wishlist",
            extra_trigger: ".my_wish_quantity:contains(1)",
            trigger: ".my_wish_quantity",
        },     
        {
            content: "add item to cart",
            trigger: 'a.o_wish_add:first',
        },
    ]
);

});