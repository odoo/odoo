/** @odoo-module **/

import { registry } from "@web/core/registry";
import * as Utils from "../helpers/utils";
import * as CartPage from "../helpers/cart_page";
import * as LandingPage from "../helpers/landing_page";
import * as ProductPage from "../helpers/product_page";
import * as StandNumberPage from "../helpers/stand_number_page";

registry.category("web_tour.tours").add("self_kiosk_each_table_takeaway_in", {
    test: true,
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Eat In"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Order"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Pay"),
        ...StandNumberPage.selectStandNumber("3"),
        Utils.clickBtn("Close"),
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Eat In"),
        Utils.checkIsDisabledBtn("Order"),
    ],
});

registry.category("web_tour.tours").add("self_kiosk_each_table_takeaway_out", {
    test: true,
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Take Out"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Order"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Pay"),
        Utils.clickBtn("Close"),
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Take Out"),
        Utils.checkIsDisabledBtn("Order"),
    ],
});

registry.category("web_tour.tours").add("self_kiosk_each_counter_takeaway_in", {
    test: true,
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Eat In"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Order"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Pay"),
        Utils.clickBtn("Close"),
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Eat In"),
        Utils.checkIsDisabledBtn("Order"),
    ],
});

registry.category("web_tour.tours").add("self_kiosk_each_counter_takeaway_out", {
    test: true,
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Take Out"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Order"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Pay"),
        Utils.clickBtn("Close"),
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Take Out"),
        Utils.checkIsDisabledBtn("Order"),
    ],
});

registry.category("web_tour.tours").add("self_order_kiosk_cancel", {
    test: true,
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Take Out"),
        ProductPage.clickProduct("Coca-Cola"),
        ProductPage.clickProduct("Fanta"),
        Utils.clickBtn("Order"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        CartPage.checkProduct("Fanta", "2.53", "1"),
        CartPage.clickBack(),
        ...ProductPage.clickCancel(),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Eat In"),
        Utils.checkIsDisabledBtn("Order"),
    ],
});

registry.category("web_tour.tours").add("self_simple_order", {
    test: true,
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Order"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Pay"),
        Utils.clickBtn("Close"),
        Utils.checkIsNoBtn("My Order"),
    ],
});
