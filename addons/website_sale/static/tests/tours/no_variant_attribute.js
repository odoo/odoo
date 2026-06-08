import { registry } from "@web/core/registry";
import * as tourUtils from "@website_sale/js/tours/tour_utils";

// This tour relies on a data created from the python test.
registry.category("web_tour.tours").add('website_sale.no_variant_attribute', {
    steps: () => [
        {
            content: "check price",
            trigger: '.oe_currency_value:contains("1.00")',
        },
        ...tourUtils.addToCartFromProductPage(),
        tourUtils.goToCart(),
        {
            content: "check price is correct",
            trigger: 'h6[name="website_sale_cart_line_price"]:contains(11.0)',
        },
    ]
});
