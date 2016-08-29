odoo.define('website_sale.tour', function (require) {
'use strict';

var Tour = require('web.Tour');

Tour.register({
    id:   'shop_buy_product',
    name: "Try to buy products",
    path: '/shop',
    mode: 'test',
    steps: [
        {
            title:  "search ipod",
            element: 'form:has(input[name="search"]) a.a-submit',
            onload: function() {
                $('input[name="search"]').val("ipod");
            }
        },
        {
            title:     "select ipod",
            element:   '.oe_product_cart a:contains("iPod")',
        },
        {
            title:     "select ipod 32GB",
            waitFor:   '#product_detail',
            element:   'label:contains(32 GB) input',
        },
        {
            title:     "click on add to cart",
            waitFor:   'label:contains(32 GB) input:propChecked',
            element:   '#product_detail form[action^="/shop/cart/update"] .btn',
        },
        {
            title:     "add suggested",
            waitNot:   '#cart_products:contains("[A8767] Apple In-Ear Headphones")',
            element:   '.oe_cart a:contains("Add to Cart")',
        },
        {
            title:     "add one more iPod",
            waitFor:   '.my_cart_quantity:contains(2)',
            element:   '#cart_products tr:contains("32 GB") a.js_add_cart_json:eq(1)',
        },
        {
            title:     "remove Headphones",
            waitFor:   '#cart_products tr:contains("32 GB") input.js_quantity:propValue(2)',
            element:   '#cart_products tr:contains("Apple In-Ear Headphones") a.js_add_cart_json:first',
        },
        {
            title:     "set one iPod",
            waitNot:   '#cart_products tr:contains("Apple In-Ear Headphones")',
            element:   '#cart_products input.js_quantity',
            sampleText: '1',
        },
        {
            title:     "go to checkout",
            waitFor:   '#cart_products input.js_quantity:propValue(1)',
            element:   'a[href="/shop/checkout"]',
        },
        {
            title:     "Confirm checkout",
            waitFor:   "div.all_shipping .panel",
            element:   'a[href="/shop/confirm_order"]',
        },
        {
            title:     "select payment",
            element:   '#payment_method label:has(img[title="Wire Transfer"]) input',
        },
        {
            title:     "Pay Now",
            waitFor:   '#payment_method label:has(input:checked):has(img[title="Wire Transfer"])',
            element:   '.oe_sale_acquirer_button .btn[type="submit"]:visible',
        },
        {
            title:     "finish",
            waitFor:   '.oe_website_sale:contains("Thank you for your order")',
        }
    ]
});

});
