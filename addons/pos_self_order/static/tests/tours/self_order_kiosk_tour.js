import { registry } from "@web/core/registry";
import * as Utils from "@pos_self_order/../tests/tours/utils/common";
import * as CartPage from "@pos_self_order/../tests/tours/utils/cart_page_util";
import * as ConfirmationPage from "@pos_self_order/../tests/tours/utils/confirmation_page_util";
import * as LandingPage from "@pos_self_order/../tests/tours/utils/landing_page_util";
import * as ProductPage from "@pos_self_order/../tests/tours/utils/product_page_util";
import * as Numpad from "@point_of_sale/../tests/tours/utils/numpad_util";
import { queryFirst } from "@odoo/hoot-dom";

//
const clickOrderNowAndWaitLocation = (location = "Take Out") => [
    //Because of the background animation, clicking on order now
    //may not do anything... so we'll click until we get to take out
    {
        trigger: ".btn:contains(order now)",
        async run(actions) {
            await new Promise((resolve) => {
                const interval = setInterval(() => {
                    actions.click();
                    if (queryFirst(`.o_kiosk_eating_location_box h3:contains(${location})`)) {
                        clearInterval(interval);
                        resolve();
                    }
                }, 300);
            });
        },
    },
    LandingPage.selectLocation(location),
];

registry.category("web_tour.tours").add("self_kiosk_each_table_takeaway_in", {
    checkDelay: 100,
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        ...clickOrderNowAndWaitLocation("Eat In"),
        ProductPage.checkReferenceNotInProductName("Coca-Cola", "12345"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Order"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Pay"),
        Numpad.click("3"),
        Utils.clickBtn("Pay"),
        Utils.clickBtn("Close"),
        Utils.checkIsNoBtn("My Order"),
        ...clickOrderNowAndWaitLocation("Eat In"),
        Utils.checkIsDisabledBtn("Order"),
    ],
});

registry.category("web_tour.tours").add("self_kiosk_each_table_takeaway_out", {
    checkDelay: 100,
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        ...clickOrderNowAndWaitLocation("Take Out"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Order"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Pay"),
        Utils.clickBtn("Close"),
        Utils.checkIsNoBtn("My Order"),
        ...clickOrderNowAndWaitLocation("Take Out"),
        Utils.checkIsDisabledBtn("Order"),
    ],
});

registry.category("web_tour.tours").add("self_kiosk_each_counter_takeaway_in", {
    checkDelay: 100,
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        ...clickOrderNowAndWaitLocation("Eat In"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Order"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Pay"),
        Utils.clickBtn("Close"),
        Utils.checkIsNoBtn("My Order"),
        ...clickOrderNowAndWaitLocation("Eat In"),
        Utils.checkIsDisabledBtn("Order"),
    ],
});

registry.category("web_tour.tours").add("self_kiosk_each_counter_takeaway_out", {
    checkDelay: 100,
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        ...clickOrderNowAndWaitLocation("Take Out"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Order"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Pay"),
        Utils.clickBtn("Close"),
        Utils.checkIsNoBtn("My Order"),
        ...clickOrderNowAndWaitLocation("Take Out"),
        Utils.checkIsDisabledBtn("Order"),
    ],
});

registry.category("web_tour.tours").add("self_order_kiosk_cancel", {
    checkDelay: 100,
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        ...clickOrderNowAndWaitLocation("Take Out"),
        ProductPage.clickProduct("Coca-Cola"),
        ProductPage.clickProduct("Fanta"),
        Utils.clickBtn("Order"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        CartPage.checkProduct("Fanta", "2.53", "1"),
        CartPage.clickBack(),
        ...ProductPage.clickCancel(),
        ...clickOrderNowAndWaitLocation("Eat In"),
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
