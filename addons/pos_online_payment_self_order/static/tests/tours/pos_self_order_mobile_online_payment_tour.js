import { registry } from "@web/core/registry";
import * as Utils from "@pos_self_order/../tests/tours/utils/common";
import * as CartPage from "@pos_self_order/../tests/tours/utils/cart_page_util";
import * as ProductPage from "@pos_self_order/../tests/tours/utils/product_page_util";
import * as ConfirmationPage from "@pos_self_order/../tests/tours/utils/confirmation_page_util";

registry.category("web_tour.tours").add("self_mobile_online_payment_meal_dynamic_qr", {
    steps: () => [
        Utils.checkBtn("My Order"),
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Order"),
        Utils.clickBtn("Ok"),
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Fanta"),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Fanta", "2.53", "1"),
        Utils.clickBtn("Order"),
        ConfirmationPage.isShown(),
        Utils.clickBtn("Ok"),
        Utils.clickBtn("My Order"),
        Utils.clickBtn("Pay"),
    ],
});

registry.category("web_tour.tours").add("test_online_payment_self_multi_company", {
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Pay"),
    ],
});

registry.category("web_tour.tours").add("test_kiosk_cart_restore_and_cancel", {
    steps: () => [
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Coca-Cola"),
        ProductPage.clickProduct("Fanta"),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        CartPage.checkProduct("Fanta", "2.53", "1"),
        Utils.clickBtn("Pay"),
        Utils.clickBtn("Back"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        CartPage.checkProduct("Fanta", "2.53", "1"),
        Utils.clickBackBtn(),
        ...ProductPage.clickCancel(),
    ],
});

registry.category("web_tour.tours").add("self_order_tip_amount_with_tax", {
    steps: () => [
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("15%"), // Select 15% tip
        CartPage.checkTotalPrice("2.97"), // Total with tax on tip
        Utils.clickBtn("Pay"),
    ],
});

registry.category("web_tour.tours").add("self_order_tip_amount_without_tax", {
    steps: () => [
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("15%"), // Select 15% tip
        CartPage.checkTotalPrice("2.91"), // Total without tax on tip
        Utils.clickBtn("Pay"),
    ],
});
