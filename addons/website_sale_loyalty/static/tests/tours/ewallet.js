import { registry } from "@web/core/registry";
import * as wsTourUtils from "@website_sale/js/tours/tour_utils";
import { payWithEWallet } from "@website_sale_loyalty/../tests/tours/tour_utils";

registry.category("web_tour.tours").add("website_sale_loyalty.ewallet", {
    steps: () => [
        // Add a $50 gift card to the order
        ...wsTourUtils.addToCart({ productName: "TEST - Gift Card", expectUnloadPage: true }),
        wsTourUtils.goToCart(),
        {
            content: "eWallets are payment methods, they are not offered as rewards",
            trigger: "#cart_products",
            run() {
                if (document.querySelector('button[name="o_loyalty_claim"]')) {
                    console.error("eWallets should not be claimable as rewards.");
                }
            },
        },
        {
            content: "Checkout",
            trigger: 'a[name="website_sale_main_button"]',
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "Only the eWallet available on the website is proposed",
            trigger: '[name="o_loyalty_payment_info"] [name="o_loyalty_card_code"]',
            run() {
                if (document.querySelector('select[name="o_loyalty_card_select"]')) {
                    console.error("Only one eWallet should be available on the website.");
                }
            },
        },
        ...payWithEWallet("50.00"),
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
