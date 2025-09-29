import { registry } from "@web/core/registry";
import * as tourUtils from "@website_sale/js/tours/tour_utils";

// This tour relies on a data created from the python test.
registry.category("web_tour.tours").add('tour_shop_no_variant_attribute', {
    url: '/shop?search=Test Product 3',
    steps: () => [
    {
        content: "select Test Product 3",
        trigger: ".oe_product_cart a:contains(/^Test Product 3$/)",
        run: "click",
        expectUnloadPage: true,
    },
    {
        content: "check price",
        trigger: '.oe_currency_value:contains("1.00")',
    },
    {
        content: "add to cart",
        trigger: 'a:contains(Add to cart)',
        run: "click",
    },
        tourUtils.goToCart(),
    {
        content: "check price is correct",
        trigger: 'h6[name="website_sale_cart_line_price"]:contains(11.0)',
    },
]});
