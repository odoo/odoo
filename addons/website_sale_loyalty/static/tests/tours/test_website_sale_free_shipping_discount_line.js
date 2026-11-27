import { registry } from "@web/core/registry";
import * as wsTourUtils from "@website_sale/js/tours/tour_utils";
import { payWithEWallet, submitCouponCode } from "@website_sale_loyalty/../tests/tours/tour_utils";

registry.category("web_tour.tours").add("website_sale_loyalty.update_shipping_after_discount", {
    steps: () => [
        ...wsTourUtils.addToCartFromProductPage(),
        wsTourUtils.goToCart(),
        wsTourUtils.goToCheckout(),
        wsTourUtils.selectDeliveryCarrier("delivery1"),
        ...wsTourUtils.assertCartAmounts({
            total: "100.00",
            delivery: "0.00", // $100 is over $75 `free_over` amount, so free shipping
        }),
        wsTourUtils.confirmOrder(),
        ...submitCouponCode('test-50pc'),
        ...wsTourUtils.assertCartAmounts({
            total: "55.00",
            delivery: "5.00", // $50 is below $75 `free_over` amount, so no free shipping
        }),
        {
            content: "check discount code discount doesn't apply to shipping",
            trigger: '[data-reward-type=discount] .oe_currency_value:text(- 50.00)',
        },
        // The eWallet pays the order, delivery fees included.
        ...payWithEWallet("55.00"),
        {
            content: "The order is paid",
            trigger: 'div h3:contains("Thank you for your order.")',
        },
    ],
});
