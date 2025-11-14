import { registry } from "@web/core/registry";
import * as Utils from "@pos_self_order/../tests/tours/utils/common";
import * as CartPage from "@pos_self_order/../tests/tours/utils/cart_page_util";
import * as LandingPage from "@pos_self_order/../tests/tours/utils/landing_page_util";
import * as ProductPage from "@pos_self_order/../tests/tours/utils/product_page_util";
import * as ConfirmationPage from "@pos_self_order/../tests/tours/utils/confirmation_page_util";

// self_ordering_mode == "consultation"
// session opened
// several presets
// --> Cannot order
registry
    .category("web_tour.tours")
    .add("self_order_closed_session.consultation_session_opened_several_presets", {
        steps: () =>
            [
                Utils.noTopAlert(),
                Utils.clickBtn("Order Now"),
                Utils.noTopAlert(),
                LandingPage.selectLocation("Eat In"),
                Utils.noTopAlert(),
                ProductPage.clickProduct("Coca-Cola"),
                Utils.checkIsNoBtn("Checkout"),
                Utils.clickBackBtn(),
                LandingPage.selectLocation("Eat In"),
            ].flat(),
    });

// self_ordering_mode == "mobile"
// session closed
// one "Eat In" preset
// --> Cannot order, do not select preset
registry
    .category("web_tour.tours")
    .add("self_order_closed_session.mobile_session_closed_one_eatin_preset", {
        steps: () =>
            [
                Utils.noTopAlert(),
                Utils.clickBtn("Order Now"),
                Utils.closedTopAlert(),
                Utils.checkIsNoBtn("Checkout"),
                ProductPage.clickProduct("Coca-Cola"),
                Utils.clickBackBtn(),
                Utils.checkBtn("Order Now"),
            ].flat(),
    });

// self_ordering_mode == "mobile"
// session closed
// several presets
// --> Can order if use timing preset, no tracking number
registry
    .category("web_tour.tours")
    .add("self_order_closed_session.mobile_session_closed_several_presets", {
        steps: () =>
            [
                Utils.noTopAlert(),
                Utils.clickBtn("Order Now"),
                // Utils.noTopAlert(),
                // LandingPage.selectLocation("Eat In"),
                // Utils.closedTopAlert(),
                // ProductPage.clickProduct("Coca-Cola"),
                // Utils.checkIsNoBtn("Checkout"),
                // Utils.clickBackBtn(),
                // Utils.noTopAlert(),

                LandingPage.selectLocation("Takeaway"),
                // Utils.nextAvailabilityTopAlert(),
                ProductPage.clickProduct("Coca-Cola"),
                Utils.clickBtn("Checkout"),
                Utils.clickBtn("Order"),
                CartPage.selectRandomValueInInput(".slot-select"),
                CartPage.fillInput("Name", "Self-Order-1"),
                Utils.clickBtn("Continue"),

                ConfirmationPage.isShown(),
                ConfirmationPage.orderNumberShown(),
                ConfirmationPage.orderNumberIs("Self-Order-1", ""),
                Utils.clickBtn("Ok"),
            ].flat(),
    });

// self_ordering_mode == "mobile"
// session opening control (the session exists but not loaded in the SELF)
// several presets
// --> Can order, tracking number
registry
    .category("web_tour.tours")
    .add("self_order_closed_session.mobile_session_opening_control_several_presets", {
        steps: () =>
            [
                Utils.noTopAlert(),
                Utils.clickBtn("Order Now"),
                Utils.noTopAlert(),
                LandingPage.selectLocation("Eat In"),
                Utils.closedTopAlert(),
                ProductPage.clickProduct("Coca-Cola"),
                Utils.checkIsNoBtn("Checkout"),
                Utils.clickBackBtn(),
                Utils.noTopAlert(),

                LandingPage.selectLocation("Takeaway"),
                Utils.nextAvailabilityTopAlert(),
                ProductPage.clickProduct("Coca-Cola"),
                Utils.clickBtn("Checkout"),
                Utils.clickBtn("Order"),
                CartPage.selectRandomValueInInput(".slot-select"),
                CartPage.fillInput("Name", "Self-Order-1"),
                Utils.clickBtn("Continue"),

                ConfirmationPage.isShown(),
                ConfirmationPage.orderNumberShown(),
                ConfirmationPage.orderNumberIs("S", "1"),
                Utils.clickBtn("Ok"),
            ].flat(),
    });

// self_ordering_mode == "mobile"
// session opened
// several presets
// --> Can order
registry
    .category("web_tour.tours")
    .add("self_order_closed_session.mobile_session_opened_several_presets", {
        steps: () =>
            [
                Utils.noTopAlert(),
                Utils.clickBtn("Order Now"),
                LandingPage.selectLocation("Eat In"),
                Utils.noTopAlert(),
                ProductPage.clickProduct("Coca-Cola"),
                Utils.checkBtn("Checkout"),
                ProductPage.clickCancel(),
                Utils.noTopAlert(),

                Utils.clickBtn("Order Now"),
                LandingPage.selectLocation("Takeaway"),
                Utils.noTopAlert(),
                ProductPage.clickProduct("Coca-Cola"),
                Utils.clickBtn("Checkout"),
                Utils.clickBtn("Order"),
                CartPage.selectRandomValueInInput(".slot-select"),
                CartPage.fillInput("Name", "Self-Order-1"),
                Utils.clickBtn("Continue"),

                ConfirmationPage.isShown(),
                ConfirmationPage.orderNumberShown(),
                ConfirmationPage.orderNumberIs("S", "1"),
                Utils.clickBtn("Ok"),
            ].flat(),
    });

// self_ordering_mode == "kiosk"
// session opened (always opened for a kiosk)
// several presets
// --> Can order
registry
    .category("web_tour.tours")
    .add("self_order_closed_session.kiosk_session_opened_several_presets", {
        steps: () =>
            [
                Utils.noTopAlert(),
                Utils.clickBtn("Order Now"),
                LandingPage.selectLocation("Eat In"),
                Utils.noTopAlert(),
                ProductPage.clickProduct("Coca-Cola"),
                Utils.checkBtn("Checkout"),
                ProductPage.clickCancel(),
                Utils.noTopAlert(),

                Utils.clickBtn("Order Now"),
                LandingPage.selectLocation("Takeaway"),
                Utils.noTopAlert(),
                ProductPage.clickProduct("Coca-Cola"),
                Utils.clickBtn("Checkout"),
                Utils.clickBtn("Order"),
                CartPage.selectRandomValueInInput(".slot-select"),
                CartPage.fillInput("Name", "Self-Order-1"),
                Utils.clickBtn("Continue"),

                ConfirmationPage.isShown(),
                ConfirmationPage.orderNumberShown(),
                ConfirmationPage.orderNumberIs("K", "1"),
                Utils.clickBtn("Close"),
            ].flat(),
    });
