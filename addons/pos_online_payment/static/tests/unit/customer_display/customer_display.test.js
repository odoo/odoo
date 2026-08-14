import { expect, test } from "@odoo/hoot";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import {
    setupCustomerDisplay,
    CustomerDisplayAssertions as Assert,
} from "@point_of_sale/../tests/unit/customer_display/utils";

definePosModels();

test("[Old Tour] CustomerDisplayTourOnlinePayment", async () => {
    const [store, order] = await setupCustomerDisplay();
    await store.addLineToCurrentOrder({ product_tmpl_id: 5 });
    // Start online payment
    const pm = store.models["pos.payment.method"].get(1);
    pm.name = "Online";
    order.addPaymentline(pm);
    const QR_URL = "data:image/png;base64,iVBORw0KGgoAAAANSU/==";
    order.onlinePaymentData = { amount: "$ 3.45", qrCode: QR_URL };

    await Assert.hasOrderLine({ productName: "TEST", price: "3.45" });
    await Assert.hasOrderlineCount(1);
    await Assert.hasPaymentLine("Online", "3.45");

    expect(".qr-payment-card .qr-image").toHaveCount(1);
    // Finalize order
    await store.validateOrder();
    // No dialog should be shown
    await Assert.checkThankyou();
    expect(".modal").toHaveCount(0);
    // New order
    const order2 = store.addNewOrder();
    store.setOrder(order2);
    await Assert.checkWelcome();
    await Assert.hasOrderlineCount(0);

    // Create another order and Start online payment again
    await store.addLineToCurrentOrder({ product_tmpl_id: 6 });
    order2.onlinePaymentData = { amount: "$ 3.75", qrCode: QR_URL };
    await Assert.hasOrderLine({ productName: "TEST 2", price: "3.75" });
    await Assert.hasOrderlineCount(1);
    expect(".qr-payment-card .qr-image").toHaveCount(1);
});
