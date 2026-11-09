import { registry } from "@web/core/registry";
import * as wsTourUtils from "@website_sale/js/tours/tour_utils";
import { payWithGiftCard, submitCouponCode } from "@website_sale_loyalty/../tests/tours/tour_utils";

registry.category("web_tour.tours").add('website_sale_loyalty.gift_card', {
    steps: () => [
        // Add a small drawer to the order (50$)
        ...wsTourUtils.addToCart({ productName: "TEST - Small Drawer", expectUnloadPage: true }),
        wsTourUtils.goToCart(),
        ...submitCouponCode('GIFT_CARD'),
        {
            content: "Gift cards are payment methods: their code is refused as a discount",
            trigger: ".alert-danger:contains(Gift cards and eWallets cannot be applied)",
        },
        {
            content: "check that no gift card line was added",
            trigger: "#cart_products",
            run() {
                const lines = [...document.querySelectorAll("#cart_products h6")];
                if (lines.some((line) => line.textContent.includes("PAY WITH GIFT CARD"))) {
                    console.error("Gift cards should not add a line to the cart.");
                }
            },
        },
        ...submitCouponCode('10PERCENT'),
        {
            content: "Check promo",
            trigger: "#cart_products div>h6:contains(10% on your order)",
        },
        {
            content: "Click on Continue Shopping",
            trigger: "div.card-body a:contains(Continue shopping)",
            run: "click",
            expectUnloadPage: true,
        },
        ...wsTourUtils.addToCart({ productName: "TEST - Gift Card", expectUnloadPage: true }),
        wsTourUtils.goToCart({quantity: 2}),
    ],
});

registry.category("web_tour.tours").add('website_sale_loyalty.split_payment_gift_cards', {
    steps: () => [
        // Add a $50 product to the order and pay it with two gift cards ($30 + $20).
        ...wsTourUtils.addToCart({ productName: "TEST - Gift Card", expectUnloadPage: true }),
        wsTourUtils.goToCart(),
        {
            content: "Checkout",
            trigger: 'a[name="website_sale_main_button"]',
            run: "click",
            expectUnloadPage: true,
        },
        ...payWithGiftCard("GIFT_CARD_30", "30.00"),
        {
            content: "Back on the payment page, check the amount paid with the first gift card",
            trigger: 'tr[name="o_order_loyalty_payment"]:contains(Gift Card) .oe_currency_value:text(30.00)',
        },
        ...payWithGiftCard("GIFT_CARD_100", "20.00"),
        {
            content: "The order is paid",
            trigger: 'div h3:contains("Thank you for your order.")',
        },
    ],
});
