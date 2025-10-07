import { registry } from "@web/core/registry";
import * as tourUtils from "@website_sale/js/tours/tour_utils";

// This tour relies on a data created from the python test.
registry.category("web_tour.tours").add('website_sale.multi_checkbox', {
    steps: () => [
        {
            content: "check price",
            trigger: '.oe_currency_value:contains("750")',
        },
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
        {
            content: "check price of options is correct",
            trigger: '.oe_currency_value:contains("753")',
        },
        ...tourUtils.addToCartFromProductPage(),
        tourUtils.goToCart(),
        {
            content: "check price is correct",
            trigger: '#cart_products div div.text-muted>span:contains("Options: Option 1, Option 2")',
        },
    ]
});

registry.category("web_tour.tours").add('website_sale.multi_checkbox_single_value', {
    steps: () => [
        {
            content: "check price",
            trigger: '.oe_currency_value:contains("750")',
        },
        {
            content: 'click on the first option to select it',
            trigger: 'input[data-attribute-name="Toppings"][data-value-name="cheese"]',
            run: "click",
        },
        {
            content: "check price of options is correct",
            trigger: '.oe_currency_value:contains("750")',
        },
        ...tourUtils.addToCartFromProductPage(),
        tourUtils.goToCart(),
        {
            content: "check choice was correctly saved",
            trigger: '#cart_products div div.text-muted>span:contains("Toppings: cheese")',
        },
    ]
});
