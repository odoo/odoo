/** @odoo-module **/

import { registry } from "@web/core/registry";
import * as wsTourUtils from "@website_sale/js/tours/tour_utils";

registry.category("web_tour.tours").add("sale_subscription_product_variants", {
    steps: () => [
        {
            content: "Trigger first period (Month)",
            trigger: "input[title='Monthly']",
            run: "click",
        },
        {
            content: "Trigger second period (2 Months)",
            trigger: "input[title='2 Months']",
            run: "click",
        },
        {
            content: "Trigger third period (Yearly)",
            trigger: "input[title='Yearly']",
            run: "click",
        },
    ],
});

registry.category("web_tour.tours").add("sale_subscription_add_to_cart", {
    steps: () => [
        {
            trigger: "body h1:contains(TestProduct2)",
        },
        {
            content: "Trigger another plan",
            trigger: ".product_price .plan_select",
            run: `selectByLabel Yearly: $ 100.00`,
        },
        {
            content: "Trigger a variant",
            trigger: "input[title='White']",
            run: "check",
        },
        {
            content: "click on add to cart",
            trigger: "#add_to_cart",
            run: "click",
        },
        wsTourUtils.goToCart(),
        {
            content: "Check the price of the product that has been added",
            trigger:
                "div[name='website_sale_cart_line_price'] .oe_currency_value:contains(\"100.00\")",
            run: "click",
        },
    ],
});
