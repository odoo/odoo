odoo.define('website_sale.tour_shop_deleted_archived_variants', function (require) {
'use strict';

var tour = require('web_tour.tour');
var base = require('web_editor.base');

// This tour relies on a data created from the python test.
tour.register('tour_shop_deleted_archived_variants', {
    test: true,
    url: '/shop?search=Test Product',
    wait_for: base.ready(),
},
[
    {
        content: "select Test Product",
        trigger: '.oe_product_cart a:containsExact("Test Product")',
    },
    {
        content: "check price (3rd variant)",
        trigger: '.oe_currency_value:contains("31.00")'
    },
    {
        content: "click on the second variant",
        trigger: 'input[data-attribute_name="My Attribute"][data-value_name="My Value 2"]',
    },
    {
        content: "check combination is not possible",
        trigger: '.js_main_product.css_not_available .css_not_available_msg:contains("This combination does not exist.")'
    },
    {
        content: "click on the 3rd variant to reset the warning",
        trigger: 'input[data-attribute_name="My Attribute"][data-value_name="My Value 3"]',
    },
    {
        content: "check price (3rd variant)",
        trigger: '.oe_currency_value:contains("31.00")'
    },
    {
        content: "click on the first variant",
        trigger: 'input[data-attribute_name="My Attribute"][data-value_name="My Value 1"]',
    },
    {
        content: "check combination is not possible",
        trigger: '.js_main_product.css_not_available .css_not_available_msg:contains("This combination does not exist.")'
    },
    {
        content: "check add to cart not possible",
        trigger: '#add_to_cart.disabled',
        run: function () {},
    }
]);
});
