import { registry } from "@web/core/registry";
import * as wsTourUtils from "@website_sale/js/tours/tour_utils";
import { assertRewardAmounts } from "@website_sale_loyalty/../tests/tours/tour_utils";

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
        {
            content: "pay with eWallet",
            trigger: "form[name=claim_reward] button[name='o_loyalty_claim']:contains('Use')",
            run: "click",
            expectUnloadPage: true,
        },
        ...assertRewardAmounts({ discount: "- 304.00" }),
        wsTourUtils.waitForInteractionToLoad(),
        wsTourUtils.selectDeliveryCarrier("delivery1"),
        ...wsTourUtils.assertCartAmounts({ delivery: "5.00" }),
        ...assertRewardAmounts({ discount: "- 300.00", shipping: "- 5.00" }),
        {
            content: "confirm shipping method",
            trigger: ".o_total_card a[name=website_sale_main_button]",
            run: "click",
            expectUnloadPage: true,
        },
        ...wsTourUtils.pay({ expectUnloadPage: true }),
    ],
});
