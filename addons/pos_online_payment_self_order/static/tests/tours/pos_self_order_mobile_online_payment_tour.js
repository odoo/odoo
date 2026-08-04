import { registry } from "@web/core/registry";
import * as Utils from "@pos_self_order/../tests/tours/utils/common";
import * as CartPage from "@pos_self_order/../tests/tours/utils/cart_page_util";
import * as ProductPage from "@pos_self_order/../tests/tours/utils/product_page_util";

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
