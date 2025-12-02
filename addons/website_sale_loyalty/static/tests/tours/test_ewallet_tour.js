import { registry } from "@web/core/registry";
import * as wsTourUtils from "@website_sale/js/tours/tour_utils";

registry.category("web_tour.tours").add("shop_sale_ewallet", {
    url: "/shop",
    steps: () => [
        // Add a $50 gift card to the order
        ...wsTourUtils.addToCart({ productName: "TEST - Gift Card", expectUnloadPage: true }),
        wsTourUtils.goToCart(),
        {
            trigger: 'button[name="o_loyalty_claim"]:contains("Use")',
            async run(helpers) {
                const rewards = document.querySelectorAll('form[name="claim_reward"]');
                if (rewards.length === 1) {
                    await helpers.click();
                } else {
                    console.error(`Expected 1 claimable reward, got: ${rewards.length}`);
                }
            },
            expectUnloadPage: true,
        },
        {
            content: "Checkout",
            trigger: 'a[name="website_sale_main_button"]',
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "Confirm Order",
            trigger: 'button[name="o_payment_submit_button"]',
            run: "click",
            expectUnloadPage: true,
        },
        {
            trigger: 'div h3:contains("Thank you for your order.")'
        },
        {
            trigger: 'a[href="/shop/cart"]',
            run: function () {
                const cartQuantity = document.querySelector(".my_cart_quantity");
                if (cartQuantity.textContent !== "0") {
                    console.error(
                        "cart should be empty and reset after an order is paid using ewallet"
                    );
                }
            },
        },
    ],
});
