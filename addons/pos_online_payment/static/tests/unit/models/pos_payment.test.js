import { test, expect } from "@odoo/hoot";
import { setupPosEnv, getFilledOrder, createPaymentLine } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

test("isAmountEditable", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    const paymentline = createPaymentLine(store, order, card);

    // Not paid online
    expect(paymentline.isAmountEditable).toBe(true);

    // Paid online
    paymentline.online_account_payment_id = 1;
    expect(paymentline.isAmountEditable).toBe(false);
    paymentline.online_account_payment_id = false;

    // Online method on an order not paid yet
    card.type = "online";
    expect(paymentline.isAmountEditable).toBe(true);

    // Online method on a paid order
    order.state = "paid";
    expect(paymentline.isAmountEditable).toBe(false);

    // Other method on a paid order
    card.type = "bank";
    expect(paymentline.isAmountEditable).toBe(true);

    // Falls back on the payment status
    paymentline.payment_status = "waiting";
    expect(paymentline.isAmountEditable).toBe(false);
});

test("isDeletable", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    const paymentline = createPaymentLine(store, order, card);

    // Not paid online
    expect(paymentline.isDeletable).toBe(true);

    // Paid online
    paymentline.online_account_payment_id = 1;
    expect(paymentline.isDeletable).toBe(false);
    paymentline.online_account_payment_id = false;

    // Falls back on the payment status
    paymentline.payment_status = "done";
    expect(paymentline.isDeletable).toBe(false);
});
