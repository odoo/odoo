import { registry } from "@web/core/registry";
import * as wsTourUtils from "@website_sale/js/tours/tour_utils";

registry.category("web_tour.tours").add("shop_sale_ewallet", {
    url: "/shop",
    steps: () => [
        // Add a $50 gift card to the order
        ...wsTourUtils.addToCart({ productName: "TEST - Gift Card", expectUnloadPage: true }),
        wsTourUtils.goToCart(),
        {
<<<<<<< 3d4588798b4b52073d3b3e13c641ee70eb783709
            trigger: 'a[name="o_loyalty_claim"]:contains("Use")',
            async run(helpers) {
||||||| 60ec0ba98a3f73d4720ca68c77ed4c69623ee08e
            trigger: 'a:contains("Pay with eWallet")',
            run() {
=======
            trigger: 'a:contains("Pay with eWallet")',
            async run(helpers) {
>>>>>>> cbc9bdd12612311e69015b6fb3bbd59e5adba20b
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
            trigger: 'div[id="introduction"] h2:contains("Sales Order")',
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
