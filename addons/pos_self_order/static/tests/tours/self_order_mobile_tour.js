/* global posmodel */

import { registry } from "@web/core/registry";
import * as Utils from "@pos_self_order/../tests/tours/utils/common";
import * as CartPage from "@pos_self_order/../tests/tours/utils/cart_page_util";
import * as LandingPage from "@pos_self_order/../tests/tours/utils/landing_page_util";
import * as ProductPage from "@pos_self_order/../tests/tours/utils/product_page_util";
import * as ConfirmationPage from "@pos_self_order/../tests/tours/utils/confirmation_page_util";

registry.category("web_tour.tours").add("self_mobile_each_table_takeaway_in", {
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
        Utils.clickBtn("My Order"),
        ...CartPage.cancelOrder(),
        Utils.checkBtn("Order Now"),
        Utils.checkBtn("My Orders"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Eat In"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Order"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        CartPage.removeLine("Coca-Cola"),
        ProductPage.isShown(),
    ],
});

registry.category("web_tour.tours").add("self_mobile_each_table_takeaway_out", {
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
        ConfirmationPage.isShown(),
        Utils.clickBtn("Ok"),
        Utils.clickBtn("My Order"),
        Utils.clickBtn("Pay"),
        Utils.clickBtn("Ok"),
        Utils.checkBtn("Order Now"),
    ],
});

registry.category("web_tour.tours").add("self_mobile_meal_table_takeaway_out", {
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Take Out"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Order"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Order"),
        ConfirmationPage.isShown(),
        Utils.clickBtn("Ok"),
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Fanta"),
        Utils.clickBtn("Order"),
        CartPage.checkProduct("Fanta", "2.53", "1"),
        Utils.clickBtn("Order"),
        ConfirmationPage.isShown(),
        Utils.clickBtn("Ok"),
        Utils.clickBtn("My Order"),
        Utils.clickBtn("Pay"),
        Utils.clickBtn("Ok"),
        Utils.checkBtn("Order Now"),
    ],
});

registry.category("web_tour.tours").add("self_mobile_meal_counter_takeaway_in", {
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Eat In"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Order"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Order"),
        ConfirmationPage.isShown(),
        Utils.clickBtn("Ok"),
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Fanta"),
        Utils.clickBtn("Order"),
        CartPage.checkProduct("Fanta", "2.53", "1"),
        Utils.clickBtn("Order"),
        ConfirmationPage.isShown(),
        Utils.clickBtn("Ok"),
        Utils.clickBtn("My Order"),
        Utils.clickBtn("Pay"),
        Utils.clickBtn("Ok"),
        Utils.checkBtn("Order Now"),
    ],
});

registry.category("web_tour.tours").add("self_mobile_meal_counter_takeaway_out", {
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Take Out"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Order"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Order"),
        ConfirmationPage.isShown(),
        Utils.clickBtn("Ok"),
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Fanta"),
        Utils.clickBtn("Order"),
        CartPage.checkProduct("Fanta", "2.53", "1"),
        Utils.clickBtn("Order"),
        ConfirmationPage.isShown(),
        Utils.clickBtn("Ok"),
        Utils.clickBtn("My Order"),
        Utils.clickBtn("Pay"),
        Utils.clickBtn("Ok"),
        Utils.checkBtn("Order Now"),
    ],
});

registry.category("web_tour.tours").add("self_order_mobile_meal_cancel", {
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
        ConfirmationPage.isShown(),
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

registry.category("web_tour.tours").add("SelfOrderOrderNumberTour", {
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Order"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Pay"),
        ...CartPage.selectTable("1"),
        Utils.clickBtn("Ok"),
        Utils.checkIsNoBtn("Ok"),
    ],
});

registry.category("web_tour.tours").add("self_order_mobile_0_price_order", {
    steps: () =>
        [
            Utils.checkIsNoBtn("My Order"),
            Utils.clickBtn("Order Now"),
            LandingPage.selectLocation("Eat In"),
            ProductPage.clickProduct("Ketchup"),
            Utils.clickBtn("Order"),
            CartPage.checkProduct("Ketchup", "0", "1"),
            Utils.clickBtn("Pay"),
            CartPage.selectTable("3"),
            ConfirmationPage.isShown(),
            Utils.clickBtn("Ok"),
            Utils.clickBtn("My Order"),
        ].flat(),
});

registry.category("web_tour.tours").add("self_order_mobile_no_access_token", {
    steps: () =>
        [
            Utils.checkIsNoBtn("My Order"),
            Utils.clickBtn("Order Now"),
            Utils.negateStep(Utils.checkBtn("Order")),
        ].flat(),
});

const syncAnCheckTrackingNumber = {
    trigger: "body",
    run: async () => {
        const trackingNumber = posmodel.currentOrder.tracking_number;
        const posReference = posmodel.currentOrder.pos_reference;
        const noOfLines = posmodel.currentOrder.lines.length;
        const result = await posmodel.sendDraftOrderToServer();
        if (!result) {
            throw new Error("Failed to sync order with server");
        }

        if (posmodel.currentOrder.lines.length !== noOfLines) {
            throw new Error(
                `Number of lines changed after sync. Before: ${noOfLines}, After: ${posmodel.currentOrder.lines.length}`
            );
        }

        if (posmodel.currentOrder.tracking_number !== trackingNumber) {
            throw new Error(
                `Tracking number changed after sync. Before: ${trackingNumber}, After: ${posmodel.currentOrder.tracking_number}`
            );
        }
        if (posmodel.currentOrder.pos_reference !== posReference) {
            throw new Error(
                `POS reference changed after sync. Before: ${posReference}, After: ${posmodel.currentOrder.pos_reference}`
            );
        }
    },
};

registry
    .category("web_tour.tours")
    .add("test_self_order_meal_do_not_change_tracking_number_on_sync", {
        steps: () =>
            [
                Utils.checkIsNoBtn("My Order"),
                Utils.clickBtn("Order Now"),
                ProductPage.clickProduct("Coca-Cola"),
                {
                    trigger: "body",
                    run: async () => {
                        const table = posmodel.models["restaurant.table"].getFirst();
                        posmodel.currentOrder.table_id = table;
                        await posmodel.sendDraftOrderToServer();
                    },
                },
                ProductPage.clickProduct("Coca-Cola"),
                syncAnCheckTrackingNumber,
                ProductPage.clickProduct("Coca-Cola"),
                ProductPage.clickProduct("Fanta"),
                syncAnCheckTrackingNumber,
                ProductPage.clickProduct("Coca-Cola"),
                syncAnCheckTrackingNumber,
            ].flat(),
    });
