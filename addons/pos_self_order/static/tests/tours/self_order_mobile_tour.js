/** @odoo-module **/

import { registry } from "@web/core/registry";
import * as Utils from "@pos_self_order/../tests/tours/utils/common";
import * as CartPage from "@pos_self_order/../tests/tours/utils/cart_page_util";
import * as LandingPage from "@pos_self_order/../tests/tours/utils/landing_page_util";
import * as ProductPage from "@pos_self_order/../tests/tours/utils/product_page_util";

registry.category("web_tour.tours").add("self_mobile_each_table_takeaway_in", {
    test: true,
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Eat In"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Order"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Pay"),
        ...CartPage.selectTable("3"),
        Utils.clickBtn("Ok"),
        Utils.checkIsNoBtn("Order Now"),
        Utils.clickBtn("My Order"),
        Utils.clickBtn("Pay"),
        Utils.clickBtn("Ok"),
        Utils.checkIsNoBtn("Order Now"),
    ],
});

registry.category("web_tour.tours").add("self_mobile_each_table_takeaway_out", {
    test: true,
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Take Out"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Order"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Pay"),
        Utils.clickBtn("Ok"),
        Utils.checkIsNoBtn("Order Now"),
        Utils.clickBtn("My Order"),
        Utils.clickBtn("Pay"),
        Utils.clickBtn("Ok"),
        Utils.checkIsNoBtn("Order Now"),
    ],
});

registry.category("web_tour.tours").add("self_mobile_each_counter_takeaway_in", {
    test: true,
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Eat In"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Order"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Pay"),
        Utils.clickBtn("Ok"),
        Utils.checkIsNoBtn("Order Now"),
        Utils.clickBtn("My Order"),
        Utils.clickBtn("Pay"),
        Utils.clickBtn("Ok"),
        Utils.checkIsNoBtn("Order Now"),
    ],
});

registry.category("web_tour.tours").add("self_mobile_each_counter_takeaway_out", {
    test: true,
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Take Out"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Order"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Pay"),
        Utils.clickBtn("Ok"),
        Utils.checkIsNoBtn("Order Now"),
        Utils.clickBtn("My Order"),
        Utils.clickBtn("Pay"),
        Utils.clickBtn("Ok"),
        Utils.checkIsNoBtn("Order Now"),
    ],
});

registry.category("web_tour.tours").add("self_mobile_meal_table_takeaway_in", {
    test: true,
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Eat In"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Order"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Order"),
        ...CartPage.selectTable("3"),
        Utils.clickBtn("Ok"),
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Fanta"),
        Utils.clickBtn("Order"),
        CartPage.checkProduct("Fanta", "2.53", "1"),
        Utils.clickBtn("Order"),
        Utils.clickBtn("Ok"),
        Utils.clickBtn("My Order"),
        Utils.clickBtn("Pay"),
        Utils.clickBtn("Ok"),
        Utils.checkBtn("Order Now"),
    ],
});

registry.category("web_tour.tours").add("self_mobile_meal_table_takeaway_out", {
    test: true,
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Take Out"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Order"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Order"),
        Utils.clickBtn("Ok"),
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Fanta"),
        Utils.clickBtn("Order"),
        CartPage.checkProduct("Fanta", "2.53", "1"),
        Utils.clickBtn("Order"),
        Utils.clickBtn("Ok"),
        Utils.clickBtn("My Order"),
        Utils.clickBtn("Pay"),
        Utils.clickBtn("Ok"),
        Utils.checkBtn("Order Now"),
    ],
});

registry.category("web_tour.tours").add("self_mobile_meal_counter_takeaway_in", {
    test: true,
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Eat In"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Order"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Order"),
        Utils.clickBtn("Ok"),
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Fanta"),
        Utils.clickBtn("Order"),
        CartPage.checkProduct("Fanta", "2.53", "1"),
        Utils.clickBtn("Order"),
        Utils.clickBtn("Ok"),
        Utils.clickBtn("My Order"),
        Utils.clickBtn("Pay"),
        Utils.clickBtn("Ok"),
        Utils.checkBtn("Order Now"),
    ],
});

registry.category("web_tour.tours").add("self_mobile_meal_counter_takeaway_out", {
    test: true,
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Take Out"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Order"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Order"),
        Utils.clickBtn("Ok"),
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Fanta"),
        Utils.clickBtn("Order"),
        CartPage.checkProduct("Fanta", "2.53", "1"),
        Utils.clickBtn("Order"),
        Utils.clickBtn("Ok"),
        Utils.clickBtn("My Order"),
        Utils.clickBtn("Pay"),
        Utils.clickBtn("Ok"),
        Utils.checkBtn("Order Now"),
    ],
});

registry.category("web_tour.tours").add("self_order_mobile_meal_cancel", {
    test: true,
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Take Out"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Order"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        CartPage.clickBack(),
        ...ProductPage.clickCancel(),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Take Out"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Order"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Order"),
        Utils.clickBtn("Ok"),
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Fanta"),
        Utils.clickBtn("Order"),
        CartPage.clickBack(),
        ...ProductPage.clickCancel(),
        Utils.clickBtn("My Order"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.checkBtn("Pay"),
    ],
});

registry.category("web_tour.tours").add("self_order_mobile_each_cancel", {
    test: true,
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Take Out"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Order"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        CartPage.clickBack(),
        ...ProductPage.clickCancel(),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Take Out"),
        Utils.checkIsDisabledBtn("Order"),
        ProductPage.clickProduct("Fanta"),
        Utils.clickBtn("Order"),
        CartPage.checkProduct("Fanta", "2.53", "1"),
        Utils.clickBtn("Pay"),
        Utils.clickBtn("Ok"),
        Utils.checkIsNoBtn("Order Now"),
        Utils.clickBtn("My Order"),
        CartPage.checkProduct("Fanta", "2.53", "1"),
        Utils.checkBtn("Pay"),
    ],
});
