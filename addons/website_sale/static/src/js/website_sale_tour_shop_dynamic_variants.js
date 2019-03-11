odoo.define('website_sale.tour_shop_dynamic_variants', function (require) {
'use strict';

var tour = require('web_tour.tour');
var base = require('web_editor.base');

// This tour relies on a data created from the python test.
tour.register('tour_shop_dynamic_variants', {
    test: true,
    url: '/shop?search=Dynamic Product',
    wait_for: base.ready(),
},
[
    {
        content: "select Dynamic Product",
        trigger: '.oe_product_cart a:containsExact("Dynamic Product")',
    },
    {
        content: "click on the second variant",
        trigger: 'input[data-attribute_name="Dynamic Attribute"][data-value_name="Dynamic Value 2"]',
    },
    {
        content: "wait for variant to be loaded",
        trigger: '.oe_price .oe_currency_value:contains("0.00")',
        run: function () {},
    },
    {
        content: "click add to cart",
        extra_trigger: 'body:has(input[type="hidden"][name="product_id"][value=0])',
        trigger: '#add_to_cart',
    },
    {
        content: "check the variant is in the cart",
        trigger: 'td.td-product_name:contains(Dynamic Product (Dynamic Value 2))',
    },
]);
});
