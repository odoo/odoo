odoo.define('website_sale_delivery.tour', function (require) {
'use strict';

var tour = require("web_tour.tour");

tour.register('check_free_delivery', {
        test: true,
        url: '/shop?search=office chair black',
},
    [
        // Part 1: Check free delivery
        {
            content: "select office chair black",
            trigger: '.oe_product_cart a:contains("Office Chair Black TEST")',
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
        // Part 2: check multiple delivery & price loaded asynchronously
        {
            content: "Ensure price was loaded asynchronously",
            extra_trigger: '#delivery_carrier input[name="delivery_type"]:checked',
            trigger: '#delivery_method .o_delivery_carrier_select:contains("20.0"):contains("The Poste")',
            run: function () {}, // it's a check
        },
        {
            content: "Click on Pay Now",
            trigger: 'button[id="o_payment_form_pay"]:visible:not(:disabled)',
        },
        {
            content: "Confirmation page should be shown",
            trigger: '#oe_structure_website_sale_confirmation_1',
            run: function () {}, // it's a check
        }
    ]);
});
