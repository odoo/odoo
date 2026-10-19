/* global posmodel */

import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import * as Utils from "@pos_self_order/../tests/tours/utils/common";
import * as CartPage from "@pos_self_order/../tests/tours/utils/cart_page_util";
import * as LandingPage from "@pos_self_order/../tests/tours/utils/landing_page_util";
import * as ProductPage from "@pos_self_order/../tests/tours/utils/product_page_util";
import * as ConfirmationPage from "@pos_self_order/../tests/tours/utils/confirmation_page_util";
import * as Notification from "@point_of_sale/../tests/generic_helpers/notification_util";

registry.category("web_tour.tours").add("self_mobile_each_table_takeaway_out", {
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Test-Takeout"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Order"),
        CartPage.fillInput("Name", "Dr Dre"),
        CartPage.fillInput("Phone", "490904390"),
        Utils.clickBtn("Continue"),
        Utils.clickBtn("Ok"),
        Utils.checkIsNoBtn("Order Now"),
        Utils.clickBtn("My Order"),
        Utils.checkIsNoBtn("Order"),
        CartPage.clickBack(),
        Utils.checkIsNoBtn("Order Now"),
    ],
});

registry.category("web_tour.tours").add("SelfOrderOrderNumberTour", {
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Checkout"),
        Utils.clickBtn("Order"),
        ...CartPage.selectTable("101"),
        Utils.clickBtn("Ok"),
        Utils.checkIsNoBtn("Ok"),
    ],
});

const createPaidOrder = [
    Utils.clickBtn("Order Now"),
    ProductPage.clickProduct("Ketchup"),
    Utils.clickBtn("Checkout"),
    CartPage.checkProduct("Ketchup", "0", "1"),
    Utils.clickBtn("Order"),
    ConfirmationPage.isShown(),
    Utils.clickBtn("Ok"),
];

registry.category("web_tour.tours").add("test_order_sequence_in_self", {
    steps: () =>
        [...createPaidOrder, ...createPaidOrder, ...createPaidOrder, ...createPaidOrder].flat(),
});

registry.category("web_tour.tours").add("test_self_order_table_no_more_sharing-meal_mode", {
    steps: () =>
        [
            Utils.checkIsNoBtn("My Order"),
            Utils.clickBtn("Order Now"),
            Utils.checkIsDisabledBtn("Checkout"),
        ].flat(),
});

registry.category("web_tour.tours").add("self_order_mobile_join_via_qr", {
    steps: () =>
        [
            Utils.clickBtn("My Order"),
            CartPage.checkProduct("Coca-Cola", "2.53", "1"),
            CartPage.clickBack(),
            Utils.clickBtn("Order Now"),
            ProductPage.clickProduct("Coca-Cola"),
            Utils.clickBtn("Checkout"),
            CartPage.checkProduct("Coca-Cola", "2.53", "1"),
            Utils.clickBtn("Order"),
            ConfirmationPage.isShown(),
            Utils.clickBtn("Ok"),
        ].flat(),
});

registry.category("web_tour.tours").add("test_delete_mobile_order_from_backend", {
    steps: () =>
        [
            Utils.checkIsNoBtn("My Order"),
            Utils.clickBtn("Order Now"),
            ProductPage.clickProduct("Coca-Cola"),
            Utils.clickBtn("Checkout"),
            CartPage.checkProduct("Coca-Cola", "2.53", "1"),
            Utils.clickBtn("Order"),
            ConfirmationPage.isShown(),
            Utils.clickBtn("Ok"),
            Utils.checkIsNoBtn("Order Now"),
            {
                trigger: "body",
                run: async () =>
                    await rpc(`/pos-self-order/test-delete-order-from-backend/`, {
                        order_ids: [posmodel.currentOrder.id],
                    }),
            },
            Utils.clickBtn("Order Now"),
            ProductPage.isShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("self_order_mobile_pay_warns_on_stale_cart", {
    steps: () =>
        [
            Utils.clickBtn("Order Now"),
            ProductPage.clickProduct("Coca-Cola"),
            Utils.clickBtn("Checkout"),
            CartPage.checkProduct("Coca-Cola", "2.53", "1"),
            Utils.clickBtn("Order"),
            ConfirmationPage.isShown(),
            Utils.clickBtn("Ok"),
            {
                content: "Simulate another device changing the order's qty server-side",
                trigger: "body",
                run: async () => {
                    const line = posmodel.currentOrder.lines[0];
                    await rpc(`/pos-self-order/test-modify-line-qty-from-backend/`, {
                        line_id: line.id,
                        qty: 5,
                    });
                },
            },
            Utils.clickBtn("Order Now"),
            ProductPage.clickProduct("Fanta"),
            Utils.clickBtn("Checkout"),
            CartPage.checkProduct("Fanta", "2.53", "1"),
            Utils.clickBtn("Order"),
            Notification.has(
                "Your order was just updated. Please review your cart before paying.",
                "warning"
            ),
            Utils.clickBtn("Order"),
            ConfirmationPage.isShown(),
            Utils.clickBtn("Ok"),
            Utils.clickBtn("My Order"),
            CartPage.checkProduct("Coca-Cola", "12.65", "5"),
            CartPage.checkProduct("Fanta", "2.53", "1"),
        ].flat(),
});

registry.category("web_tour.tours").add("self_order_mobile_dynamic_qr_blocked", {
    steps: () =>
        [
            {
                content: "The staff-QR-only banner is shown",
                trigger:
                    ".o-self-closed:contains('Self-ordering is only available through the QR code provided by our staff. You can still view the menu.')",
            },
            Utils.clickBtn("Order Now"),
            {
                content: "No ordering action is available without a valid QR-joined order",
                trigger: Utils.negate(".o_pos_landing_footer"),
            },
        ].flat(),
});
