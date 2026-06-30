import { expect, queryOne, test } from "@odoo/hoot";
import { definePosModels } from "../data/generate_model_definitions";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { setupCustomerDisplay, CustomerDisplayAssertions as Assert } from "./utils";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { isVisible } from "@html_editor/utils/dom_info";

definePosModels();

test("[Old Tour] CustomerDisplayTour", async () => {
    const [store, order] = await setupCustomerDisplay();
    // Line1 - unselected line
    await store.addLineToCurrentOrder({ product_tmpl_id: 5 });
    order.deselectOrderline();
    await Assert.hasOrderLine({ productName: "TEST", price: "3.45" });
    await Assert.hasOrderlineCount(1);
    expect(store.customerDisplay.data.selectedLineUuid).toBeEmpty();
    // Line2 - selected line
    await store.addLineToCurrentOrder({ product_tmpl_id: 6 });
    await Assert.hasOrderLine({ productName: "TEST 2", price: "3.75" });
    await Assert.hasOrderlineCount(2);
    expect(store.customerDisplay.data.selectedLineUuid).toBe(order.lines[1].uuid);
    // add payment Line
    const cashPm = store.models["pos.payment.method"].get(1);
    order.addPaymentline(cashPm);
    await Assert.hasPaymentLine("Cash", "7.20");
    // Pay Order
    await store.validateOrder();
    await Assert.checkThankyou();
    // New Order
    const order2 = store.addNewOrder();
    store.setOrder(order2);
    await Assert.checkWelcome();
    await Assert.hasOrderlineCount(0);
    // Navigate to screen saver
    store.navigate("SaverScreen");
    await Assert.checkScreenSaver();
});

test("[Old Tour] CustomerDisplayTourScroll", async () => {
    // OLD test Name - `test_customer_display_scroll`
    patchWithCleanup(PosOrderline.prototype, {
        canBeMergedWith(orderline) {
            return false; // Ovveride so that we could add multiple line for the same products in the order.
        },
    });
    const [store] = await setupCustomerDisplay();
    for (let i = 0; i < 20; i++) {
        await store.addLineToCurrentOrder({ product_tmpl_id: 5 });
    }
    await Assert.hasOrderlineCount(20);

    const orderContainer = queryOne(".order-container");
    const orderLine = queryOne(".orderline:last-child");

    const waitForScroll = (el) =>
        new Promise((resolve) => {
            const check = () => (el.scrollTop > 0 ? resolve() : requestAnimationFrame(check));
            check();
        });

    await waitForScroll(orderContainer);

    expect(orderContainer.scrollTop).toBeGreaterThan(0);
    expect(isVisible(orderLine)).toBe(true);
});

test("[Old Tour] CustomerDisplayTourWithQr", async () => {
    // OLD test Name - `test_customer_display_qr`
    const [store, order] = await setupCustomerDisplay();

    await store.addLineToCurrentOrder({ product_tmpl_id: 5 });
    await Assert.hasOrderLine({ productName: "TEST", price: "3.45" });
    // Card payment
    const cardPm = store.models["pos.payment.method"].get(2);
    const { status, data: paymentLine } = order.addPaymentline(cardPm);
    paymentLine.uiState.qrCode = "data:image/png;base64,iVBORw0KGgoAAAANSU/==";
    await Assert.hasOrderlineCount(1);
    // QR displayed while payment is pending
    expect(status).toBe(true);
    expect(".qr-payment-card").toHaveCount(1);
    expect("img[alt='QR Code']").toHaveCount(1);
    expect("h3:contains('Amount:'):contains(3.45)").toHaveCount(1);
    // Confirm payment
    await store.validateOrder();
    await Assert.checkThankyou();
});
