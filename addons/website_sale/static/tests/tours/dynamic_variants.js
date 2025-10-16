import { registry } from "@web/core/registry";
import * as tourUtils from "@website_sale/js/tours/tour_utils";

// This tour relies on a data created from the python test.
registry.category("web_tour.tours").add('website_sale.dynamic_variants', {
    steps: () => [
        {
            content: "click on the second variant",
            trigger: 'input[data-attribute-name="Dynamic Attribute"][data-value-name="Dynamic Value 2"]',
            run: "click",
        },
        {
            content: "wait for variant to be loaded",
            trigger: '.oe_price .oe_currency_value:contains("0.00")',
        },
        {
            trigger: '.js_product button[name="add_to_cart"]:not([data-product-id])',
        },
        ...tourUtils.addToCartFromProductPage(),
        tourUtils.goToCart(),
        ...tourUtils.assertCartContains({
            productName: 'Dynamic Product',
            combinationName: 'Dynamic Value 2',
        }),
    ]
});
