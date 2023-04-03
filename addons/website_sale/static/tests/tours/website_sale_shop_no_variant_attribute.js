/** @odoo-module **/

import { registry } from "@web/core/registry";
import tourUtils from "website_sale.tour_utils";

// This tour relies on a data created from the python test.
registry.category("web_tour.tours").add('tour_shop_no_variant_attribute', {
    test: true,
    url: '/shop?search=Test Product 3',
    steps: [
    {
        content: "select Test Product 3",
        trigger: '.oe_product_cart a:containsExact("Test Product 3")',
    },
    {
        content: "check price",
        trigger: '.oe_currency_value:contains("1.00")',
        run: function () {},
    },
    {
        content: "add to cart",
        trigger: 'a:contains(ADD TO CART)',
    },
        tourUtils.goToCart(),
    {
        content: "check no_variant value is present",
        trigger: '.td-product_name:contains(No Variant Attribute: No Variant Value)',
        extra_trigger: '#cart_products',
        run: function () {},
    },
    {
        content: "check price is correct",
        trigger: '.td-price:contains(11.0)',
        run: function () {},
    },
]});
