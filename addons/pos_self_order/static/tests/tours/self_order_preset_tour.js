import { registry } from "@web/core/registry";
import * as Utils from "@pos_self_order/../tests/tours/utils/common";
import * as CartPage from "@pos_self_order/../tests/tours/utils/cart_page_util";
import * as LandingPage from "@pos_self_order/../tests/tours/utils/landing_page_util";
import * as ProductPage from "@pos_self_order/../tests/tours/utils/product_page_util";

registry.category("web_tour.tours").add("self_order_preset_eat_in_tour", {
    steps: () => [
        // Test preset "Eat in" location with table
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Eat in"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Order"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Pay"),
        ...CartPage.selectTable("1"),
        Utils.clickBtn("Ok"),
    ],
});

registry.category("web_tour.tours").add("self_order_preset_takeaway_tour", {
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Takeaway"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Order"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Pay"),
        CartPage.fillInput("Name", "Dr Dre"),
        Utils.clickBtn("Continue"),
        Utils.clickBtn("Ok"),
    ],
});

registry.category("web_tour.tours").add("self_order_preset_delivery_tour", {
    steps: () => [
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Delivery"),
        ProductPage.clickProduct("Free"),
        Utils.clickBtn("Order"),
        CartPage.checkProduct("Free", "0", "1"),
        Utils.clickBtn("Pay"),
        CartPage.fillInput("Name", "Dr Dre"),
        CartPage.fillInput("Phone", "0490 90 43 90"),
        CartPage.fillInput("Street and Number", "Rue du Bronx 90"),
        CartPage.fillInput("Zip", "9999"),
        CartPage.fillInput("City", "New York"),
        Utils.clickBtn("Continue"),
        Utils.clickBtn("Ok"),

        // Check if the partner is available in cache
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Delivery"),
        ProductPage.clickProduct("Free"),
        Utils.clickBtn("Order"),
        CartPage.checkProduct("Free", "0", "1"),
        Utils.clickBtn("Pay"),
        CartPage.selectRandomValueInInput(".partner-select"),
        Utils.clickBtn("Continue"),
        Utils.clickBtn("Ok"),
    ],
});

registry.category("web_tour.tours").add("self_order_preset_slot_tour", {
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Takeaway"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Order"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Pay"),
        CartPage.selectRandomValueInInput(".slot-select"),
        CartPage.fillInput("Name", "Dr Dre"),
        Utils.clickBtn("Continue"),
        Utils.clickBtn("Ok"),
    ],
});
