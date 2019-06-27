odoo.define('website_sale_delivery.tour', function (require) {
'use strict';

var tour = require("web_tour.tour");

tour.register('check_free_delivery', {
        test: true,
        url: '/shop?search=office chair black',
},
    [
        {
            content: "select office chair black",
            trigger: '.oe_product_cart:first a:contains("Office Chair Black")',
        },
        {
            content: "click on add to cart",
            trigger: '#product_details #add_to_cart',
        },
        {
            content: "go to checkout",
            extra_trigger: '#cart_products input.js_quantity:propValue(1)',
            trigger: 'a[href*="/shop/checkout"]',
        },
        {
            content: "Check Free Delivery value to be zero",
            extra_trigger: '#delivery_carrier label:containsExact("Delivery Now Free Over 10")',
            trigger: "#delivery_carrier span:contains('0.0')"
        },
    ]);
});
