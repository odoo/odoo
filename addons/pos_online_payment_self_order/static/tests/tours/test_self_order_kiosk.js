/** @odoo-module **/

import { registry } from "@web/core/registry";
import * as Utils from "@pos_self_order/../tests/helpers/utils";
import * as CartPage from "@pos_self_order/../tests/helpers/cart_page";
import * as ProductPage from "@pos_self_order/../tests/helpers/product_page";

registry.category("web_tour.tours").add("tour_kiosk_online_payment_cart_check", {
    test: true,
    steps: () => [
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Coca-Cola"),
        ProductPage.clickProduct("Fanta"),
        Utils.clickBtn("Order"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        CartPage.checkProduct("Fanta", "2.53", "1"),
        Utils.clickBtn("Pay"),
        Utils.clickBtn("Back"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        CartPage.checkProduct("Fanta", "2.53", "1"),
        {
            content: "Last tour step",
            trigger: "body",
            isCheck: true,
        },
    ],
});
