odoo.define('website_sale_delivery.tour', function (require) {
'use strict';

var base = require('web_editor.base');
var tour = require("web_tour.tour");

tour.register('check_free_delivery', {
        test: true,
        url: '/shop?search=conference chair',
        wait_for: base.ready(),
},
    [
        {
            content: "select conference chair",
            trigger: '.oe_product_cart:first a:contains("Conference Chair")',
        },
        {
            content: "click on add to cart",
            extra_trigger: 'label:contains(Steel) input:propChecked',
            trigger: '#product_detail form[action^="/shop/cart/update"] .btn-primary',
        },
        {
            content: "click in modal on 'Proceed to checkout' button",
            trigger: 'button:contains("Proceed to Checkout")',
        },
        {
            content: "go to checkout",
            extra_trigger: '#cart_products input.js_quantity:propValue(1)',
            trigger: 'a[href*="/shop/checkout"]',
        },
        {
            content: "Check Free Delivery value to be zero",
            trigger: "#delivery_carrier span:contains('0.0')"
        },
    ]);
});
