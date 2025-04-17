import { registry } from "@web/core/registry";
import * as Utils from "@pos_self_order/../tests/tours/utils/common";
import * as CartPage from "@pos_self_order/../tests/tours/utils/cart_page_util";
import * as LandingPage from "@pos_self_order/../tests/tours/utils/landing_page_util";
import * as ProductPage from "@pos_self_order/../tests/tours/utils/product_page_util";
import * as ConfirmationPage from "@pos_self_order/../tests/tours/utils/confirmation_page_util";

registry.category("web_tour.tours").add("self_mobile_online_payment_meal_table", {
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Test-In"),
        ProductPage.clickProduct("Desk Pad"),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Desk Pad", "2.28", "1"),
        Utils.clickBtn("Order"),
        ...CartPage.selectTable("1"),
        Utils.clickBtn("Ok"),
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Desk Organizer"),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Desk Organizer", "5.87", "1"),
        Utils.clickBtn("Order"),
        ConfirmationPage.isShown(),
        Utils.clickBtn("Ok"),
        Utils.clickBtn("My Order"),
        Utils.clickBtn("Pay"),
    ],
});
