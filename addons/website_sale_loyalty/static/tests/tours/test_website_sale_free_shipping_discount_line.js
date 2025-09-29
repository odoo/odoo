import { registry } from "@web/core/registry";
import * as wsTourUtils from "@website_sale/js/tours/tour_utils";
import { assertRewardAmounts, submitCouponCode } from "@website_sale_loyalty/../tests/tours/tour_utils";

registry.category("web_tour.tours").add("website_sale_loyalty.update_shipping_after_discount", {
    steps: () => [
        ...wsTourUtils.addToCartFromProductPage(),
        wsTourUtils.goToCart(),
        {
            content: "use eWallet to check it doesn't impact `free_over` shipping",
            trigger: "button[name='o_loyalty_claim']:contains('Use')",
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "Check pay with eWallet is applied",
            trigger: ".o_cart_product [name=website_sale_cart_line_price]:contains(- 100.00)",
        },
        wsTourUtils.goToCheckout(),
        wsTourUtils.selectDeliveryCarrier("delivery1"),
        ...wsTourUtils.assertCartAmounts({
            total: "0.00", // $100 total is covered by eWallet
            delivery: "0.00", // $100 is over $75 `free_over` amount, so free shipping
        }),
        ...assertRewardAmounts({ discount: "- 100.00" }),
        wsTourUtils.confirmOrder(),
        ...submitCouponCode('test-50pc'),
        ...wsTourUtils.assertCartAmounts({
            total: "0.00", // $50 total is covered by eWallet
            delivery: "5.00", // $50 is below $75 `free_over` amount, so no free shipping
        }),
        {
            content: "check discount code discount doesn't apply to shipping",
            trigger: '[data-reward-type=discount] .oe_currency_value:contains(/^- 50.00$/)',
        },
        {
            content: "check eWallet discount applies to shipping ($50 for Plumbus + $5 for delivery)",
            trigger: '[data-reward-type=discount] .oe_currency_value:contains(/^- 55.00$/)',
        },
    ],
});
