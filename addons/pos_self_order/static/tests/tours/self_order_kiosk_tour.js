import { registry } from "@web/core/registry";
import * as Utils from "@pos_self_order/../tests/tours/utils/common";
import * as CartPage from "@pos_self_order/../tests/tours/utils/cart_page_util";
import * as ConfirmationPage from "@pos_self_order/../tests/tours/utils/confirmation_page_util";
import * as LandingPage from "@pos_self_order/../tests/tours/utils/landing_page_util";
import * as ProductPage from "@pos_self_order/../tests/tours/utils/product_page_util";
import * as Numpad from "@point_of_sale/../tests/generic_helpers/numpad_util";

registry.category("web_tour.tours").add("self_kiosk_each_table_takeaway_in", {
    checkDelay: 100,
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        ProductPage.checkReferenceNotInProductName("Coca-Cola", "12345"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Order"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Pay"),
        Numpad.click("3"),
        Utils.clickBtn("Pay"),
        Utils.clickBtn("Close"),
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        Utils.checkIsDisabledBtn("Order"),
    ],
});

registry.category("web_tour.tours").add("self_kiosk_each_table_takeaway_out", {
    checkDelay: 100,
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Order"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Pay"),
        Utils.clickBtn("Close"),
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        Utils.checkIsDisabledBtn("Order"),
    ],
});

registry.category("web_tour.tours").add("self_kiosk_each_counter_takeaway_in", {
    checkDelay: 100,
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Test-In"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Order"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Pay"),
        Numpad.click("3"),
        Utils.clickBtn("Pay"),
        Utils.clickBtn("Close"),
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Test-In"),
        Utils.checkIsDisabledBtn("Order"),
    ],
});

registry.category("web_tour.tours").add("self_kiosk_each_counter_takeaway_out", {
    checkDelay: 100,
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Test-Takeout"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Order"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Pay"),
        Utils.clickBtn("Close"),
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Test-Takeout"),
        Utils.checkIsDisabledBtn("Order"),
    ],
});

registry.category("web_tour.tours").add("self_order_kiosk_cancel", {
    checkDelay: 100,
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Coca-Cola"),
        ProductPage.clickProduct("Fanta"),
        Utils.clickBtn("Order"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        CartPage.checkProduct("Fanta", "2.53", "1"),
        CartPage.clickBack(),
        ...ProductPage.clickCancel(),
        Utils.clickBtn("Order Now"),
        Utils.checkIsDisabledBtn("Order"),
    ],
});

registry.category("web_tour.tours").add("self_simple_order", {
    checkDelay: 100,
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

registry.category("web_tour.tours").add("self_order_price_null", {
    checkDelay: 100,
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Order"),
        CartPage.checkProduct("Coca-Cola", "0.00", "1"),
        Utils.clickBtn("Pay"),
        ConfirmationPage.orderNumberShown(),
        Utils.checkBtn("Close"),
    ],
});

registry.category("web_tour.tours").add("self_order_language_changes", {
    checkDelay: 100,
    steps: () => [
        LandingPage.checkLanguageSelected("English"),
        LandingPage.checkCountryFlagShown("us"),
        Utils.openLanguageSelector(),
        Utils.checkLanguageIsAvailable("French"),
    ],
});

registry.category("web_tour.tours").add("test_self_order_kiosk_combo_sides", {
    steps: () => [
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Test-In"),
        ProductPage.clickProduct("Office Combo"),
        ProductPage.clickProduct("Desk Organizer"),
        {
            trigger: `.page-buttons :disabled:contains("Next")`,
        },
        ...ProductPage.setupAttribute([
            { name: "Size", value: "M" },
            { name: "Fabric", value: "Leather" },
        ]),
        Utils.clickBtn("Add to cart"),
    ],
});
