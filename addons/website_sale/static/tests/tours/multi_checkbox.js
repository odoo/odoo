import { registry } from "@web/core/registry";
import * as tourUtils from "@website_sale/js/tours/tour_utils";

// This tour relies on a data created from the python test.
registry.category("web_tour.tours").add('website_sale.multi_checkbox', {
    steps: () => [
        tourUtils.assertProductPagePrice('750.00'),
        {
            content: 'click on the first option to select it',
            trigger: 'input[data-attribute-name="Options"][data-value-name="Option 1"]',
            run: "click",
        },
        {
            content: "check third option is not available (but clickable)",
            trigger: 'input[data-value-name="Option 3"].css_not_available:not([disabled])',
        },
        {
            content: 'click on the second option to select it',
            trigger: 'input[data-attribute-name="Options"][data-value-name="Option 2"]',
            run: "click",
        },
        tourUtils.assertProductPagePrice('753.00'),
        ...tourUtils.addToCartFromProductPage(),
        tourUtils.goToCart(),
        ...tourUtils.assertCartContains({
            productName: "Product Multi",
            description: "Options: Option 1, Option 2",
        }),
    ]
});

registry.category("web_tour.tours").add('website_sale.multi_checkbox_single_value', {
    steps: () => [
        tourUtils.assertProductPagePrice('750.00'),
        {
            content: 'click on the first option to select it',
            trigger: 'input[data-attribute-name="Toppings"][data-value-name="cheese"]',
            run: "click",
        },
        tourUtils.assertProductPagePrice('750.00'),
        ...tourUtils.addToCartFromProductPage(),
        tourUtils.goToCart(),
        ...tourUtils.assertCartContains({
            productName: "Burger",
            description: "Toppings: cheese",
        }),
    ]
});
