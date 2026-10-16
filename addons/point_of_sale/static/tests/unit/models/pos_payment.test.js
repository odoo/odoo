import { expect, freezeTime, mockDate, test } from "@odoo/hoot";
import { definePosModels } from "../data/generate_model_definitions";
import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";
import { createPaymentLine, getFilledOrder, setupPosEnv } from "../utils";

const { DateTime } = luxon;

definePosModels();

test("uiState", async () => {
    mockDate("2025-01-09 12:00:00");
    freezeTime();

    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    const paymentline = createPaymentLine(store, order, card);

    expect(paymentline.uiState).toEqual({
        initStateDate: DateTime.fromISO("2025-01-09T13:00:00"),
    });
});

test("isDone", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    const paymentline = createPaymentLine(store, order, card);

    // done
    paymentline.payment_status = "done";
    expect(paymentline.isDone()).toBe(true);

    // pending
    paymentline.payment_status = "pending";
    expect(paymentline.isDone()).toBe(false);

    // no status
    paymentline.payment_status = null;
    expect(paymentline.isDone()).toBe(true);
});

test("isProcessing", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    const paymentline = createPaymentLine(store, order, card);

    const processingStatuses = [
        "waiting",
        "waiting_cancel",
        "waiting_card",
        "waiting_scan",
        "waiting_capture",
        "force_done",
    ];

    for (const status of processingStatuses) {
        paymentline.payment_status = status;
        expect(paymentline.isProcessing()).toBe(true);
    }

    // non-processing status
    paymentline.payment_status = "done";
    expect(paymentline.isProcessing()).toBe(false);

    // no status
    paymentline.payment_status = null;
    expect(paymentline.isProcessing()).toBe(false);
});

test("isRefund", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    const paymentline = createPaymentLine(store, order, card);

    // positive amount
    expect(paymentline.isRefund).toBe(false);

    // negative amount
    paymentline.amount = -10;
    expect(paymentline.isRefund).toBe(true);

    // zero amount
    paymentline.amount = 0;
    expect(paymentline.isRefund).toBe(false);
});

test("pay", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    card.payment_interface = new PaymentInterface(store, card);
    const paymentline = createPaymentLine(store, order, card, { payment_status: "pending" });

    // Successful
    card.payment_interface.sendPaymentRequest = async () => {
        expect(paymentline.payment_status).toBe("waiting");
        return true;
    };
    expect(await paymentline.pay()).toBe(true);
    expect(paymentline.payment_status).toBe("done");

    // Failed
    card.payment_interface.sendPaymentRequest = async () => false;
    expect(await paymentline.pay()).toBe(false);
    expect(paymentline.payment_status).toBe("retry");

    // Error
    card.payment_interface.sendPaymentRequest = async () => {
        throw new Error("Request failed");
    };
    await expect(paymentline.pay()).rejects.toThrow("Request failed");
    expect(paymentline.payment_status).toBe("retry");
});

test("cancelPayment", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    card.payment_interface = new PaymentInterface(store, card);
    const paymentline = createPaymentLine(store, order, card);

    // Successful
    paymentline.payment_status = "waiting_card";
    card.payment_interface.sendPaymentCancel = async () => {
        expect(paymentline.payment_status).toBe("waiting_cancel");
        return true;
    };
    expect(await paymentline.cancelPayment()).toBe(true);
    expect(paymentline.payment_status).toBe("retry");

    // Failed: back to the status before the cancel
    for (const status of ["waiting_card", "waiting_scan", "waiting"]) {
        paymentline.payment_status = status;
        card.payment_interface.sendPaymentCancel = async () => false;
        expect(await paymentline.cancelPayment()).toBe(false);
        expect(paymentline.payment_status).toBe(status);
    }

    // Error: back to the status before the cancel
    paymentline.payment_status = "waiting_scan";
    card.payment_interface.sendPaymentCancel = async () => {
        throw new Error("Cancel failed");
    };
    await expect(paymentline.cancelPayment()).rejects.toThrow("Cancel failed");
    expect(paymentline.payment_status).toBe("waiting_scan");
});

test("forceDone", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    card.payment_interface = new PaymentInterface(store, card);
    const data = { payment_status: "waiting" };
    const paymentline = createPaymentLine(store, order, card, data);

    paymentline.forceDone();
    expect(paymentline.payment_status).toBe("done");
});

test("forceCancel", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    card.payment_interface = new PaymentInterface(store, card);
    const data = { payment_status: "waiting" };
    const paymentline = createPaymentLine(store, order, card, data);

    paymentline.forceCancel();
    expect(paymentline.payment_status).toBe("retry");
});

test("canBeAdjusted", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    const paymentline = createPaymentLine(store, order, card);

    // no payment interface + is cash
    card.type = "cash";
    card.payment_method_type = "none";
    expect(paymentline.canBeAdjusted()).toBe(false);

    // no payment interface + is not cash
    card.type = "bank";
    card.payment_method_type = "none";
    expect(paymentline.canBeAdjusted()).toBe(true);

    // payment interface that supports adjustments
    card.payment_interface = { canBeAdjusted: () => true };
    expect(paymentline.canBeAdjusted()).toBe(true);

    // payment interface that does not support adjustments
    card.payment_interface = { canBeAdjusted: () => false };
    expect(paymentline.canBeAdjusted()).toBe(false);
});

test("adjustAmount", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    const paymentline = createPaymentLine(store, order, card);

    // no payment interface
    card.payment_interface = null;
    paymentline.adjustAmount(20);
    expect(paymentline.getAmount()).toBe(10);

    // payment interface that supports adjustments
    card.payment_interface = {
        sendPaymentAdjust: (uuid) => {
            const newAmount = paymentline.getAmount() + 5;
            paymentline.setAmount(newAmount);
        },
    };
    paymentline.adjustAmount(20);
    expect(paymentline.getAmount()).toBe(35); // 10 + 20 + 5
});
