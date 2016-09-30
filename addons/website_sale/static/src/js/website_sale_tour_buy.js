odoo.define('website_sale.tour', function (require) {
'use strict';

var tour = require("web_tour.tour");
var base = require("web_editor.base");

tour.register('shop_buy_product', {
    test: true,
    url: '/shop',
    wait_for: base.ready()
},
    [
        {
            content: "search ipod",
            trigger: 'form input[name="search"]',
            run: "text ipod",
        },
        {
            content: "search ipod",
            trigger: 'form:has(input[name="search"]) .oe_search_button',
        },
        {
            content: "select ipod",
            trigger: '.oe_product_cart a:contains("iPod")',
        },
        {
            content: "select ipod 32GB",
            extra_trigger: '#product_detail',
            trigger: 'label:contains(32 GB) input',
        },
        {
            content: "click on add to cart",
            extra_trigger: 'label:contains(32 GB) input:propChecked',
            trigger: '#product_detail form[action^="/shop/cart/update"] .btn',
        },
        {
            content: "add suggested",
            extra_trigger: '#wrap:not(:has(#cart_products:contains("[A8767] Apple In-Ear Headphones")))',
            trigger: '.oe_cart:has(tr:contains("32 GB")) a:contains("Add to Cart")',
        },
        {
            content: "add one more iPod",
            extra_trigger: '.my_cart_quantity:contains(2)',
            trigger: '#cart_products tr:contains("32 GB") a.js_add_cart_json:eq(1)',
        },
        {
            content: "remove Headphones",
            extra_trigger: '#cart_products tr:contains("32 GB") input.js_quantity:propValue(2)',
            trigger: '#cart_products tr:contains("Apple In-Ear Headphones") a.js_add_cart_json:first',
        },
        {
            content: "set one iPod",
            extra_trigger: '#wrap:not(:has(#cart_products tr:contains("Apple In-Ear Headphones")))',
            trigger: '#cart_products input.js_quantity',
            run: 'text 1',
        },
        {
            content: "go to checkout",
            extra_trigger: '#cart_products input.js_quantity:propValue(1)',
            trigger: 'a[href="/shop/checkout"]',
        },
        {
            content: "Confirm checkout",
            extra_trigger: "div.all_shipping .panel",
            trigger: 'a[href="/shop/confirm_order"]',
        },
        {
            content: "select payment",
            trigger: '#payment_method label:contains("Wire Transfer") input',
        },
        {
            content: "Pay Now",
            extra_trigger: '#payment_method label:contains("Wire Transfer") input:checked',
            trigger: '.oe_sale_acquirer_button .btn[type="submit"]:visible',
        },
        {
            content: "finish",
            trigger: '.oe_website_sale:contains("Thank you for your order")',
        }
    ]
);

});
