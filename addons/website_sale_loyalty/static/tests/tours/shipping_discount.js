import { registry } from "@web/core/registry";
import * as wsTourUtils from "@website_sale/js/tours/tour_utils";
import { assertRewardAmounts, payWithEWallet } from "@website_sale_loyalty/../tests/tours/tour_utils";

registry.category("web_tour.tours").add("website_sale_loyalty.check_shipping_discount", {
    steps: () => [
        {
            content: "increase product quantity",
            trigger: '#product_details input[name="add_qty"]',
            run: "edit 3",
        },
        ...wsTourUtils.addToCartFromProductPage(),
        wsTourUtils.goToCart({ quantity: 3 }),
        wsTourUtils.goToCheckout(),
        wsTourUtils.waitForInteractionToLoad(),
        wsTourUtils.selectDeliveryCarrier("delivery2"),
        ...wsTourUtils.assertCartAmounts({
            delivery: "10.00", // delivery2 is $10, ignoring shipping discount
            total: "304.00", // $100 per Plumbus, plus discounted delivery
        }),
        ...assertRewardAmounts({ shipping: "- 6.00" }),
        wsTourUtils.selectDeliveryCarrier("delivery1"),
        ...wsTourUtils.assertCartAmounts({ delivery: "5.00", total: "300.00" }),
        ...assertRewardAmounts({ shipping: "- 5.00" }),
        {
            content: "confirm delivery method",
            trigger: ".o_total_card a[name=website_sale_main_button]",
            run: "click",
            expectUnloadPage: true,
        },
        // The eWallet pays the order: it is a payment, not a discount on the order.
        ...payWithEWallet("300.00"),
        {
            content: "The order is paid",
            trigger: 'div h3:contains("Thank you for your order.")',
        },
    ],
});
