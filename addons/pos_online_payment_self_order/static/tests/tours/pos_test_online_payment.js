import { registry } from "@web/core/registry";
import * as Utils from "@pos_self_order/../tests/tours/utils/common";
import * as ProductPage from "@pos_self_order/../tests/tours/utils/product_page_util";
import * as ConfirmationPage from "@pos_self_order/../tests/tours/utils/confirmation_page_util";

registry.category("web_tour.tours").add("pos_test_online_payment", {
    steps: () => [
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Checkout"),
        {
            content: "Click pay button",
            trigger: ".btn:contains('Pay')",
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "Submit online payment",
            trigger: 'button[name="o_payment_submit_button"]:not(:disabled)',
            run: "click",
            expectUnloadPage: true,
        },
        ConfirmationPage.isShown(),
    ],
});
