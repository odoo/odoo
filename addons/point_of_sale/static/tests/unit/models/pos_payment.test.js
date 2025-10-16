import { test, expect } from "@odoo/hoot";
import { getFilledOrder, setupPosEnv, createPaymentLine } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";
import { mockDate } from "@odoo/hoot-mock";
const { DateTime } = luxon;

definePosModels();

test("uiState", async () => {
    mockDate("2025-01-09 12:00:00");
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    const paymentline = createPaymentLine(store, order, card);

    expect(paymentline.uiState).toEqual({
        qrCode: null,
        initStateDate: new DateTime.now(),
    });
});

test("updateCustomerDisplayQrCode", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    const paymentline = createPaymentLine(store, order, card);
    const qrCode = "https://example.com/qr-code";

    // Update QR code
    paymentline.updateCustomerDisplayQrCode(qrCode);
    expect(paymentline.uiState.qrCode).toBe(qrCode);

    // Clear QR code
    paymentline.updateCustomerDisplayQrCode(null);
    expect(paymentline.uiState.qrCode).toBe(null);
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
        "waitingCancel",
        "waitingCard",
        "waitingScan",
        "waitingCapture",
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

test("handlePaymentResponse", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    const paymentline = createPaymentLine(store, order, card);

    // Successful
    paymentline.payment_status = "waitingCard";
    const response = paymentline.handlePaymentResponse(true);
    expect(response).toBe(true);
    expect(paymentline.payment_status).toBe("done");

    // Failed
    paymentline.payment_status = "waitingCard";
    const responseFail = paymentline.handlePaymentResponse(false);
    expect(responseFail).toBe(false);
    expect(paymentline.payment_status).toBe("retry");
});

test("handlePaymentCancelResponse", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    const paymentline = createPaymentLine(store, order, card);

    // Successful
    paymentline.payment_status = "waitingCancel";
    const response = paymentline.handlePaymentCancelResponse(true);
    expect(response).toBe(true);
    expect(paymentline.payment_status).toBe("retry");

    // Failed - Terminal
    card.payment_method_type = "terminal";
    paymentline.payment_status = "waitingCancel";
    const responseFailTerminal = paymentline.handlePaymentCancelResponse(false);
    expect(responseFailTerminal).toBe(false);
    expect(paymentline.payment_status).toBe("waitingCard");

    // Failed - External QR
    card.payment_method_type = "external_qr";
    paymentline.payment_status = "waitingScan";
    const responseFailNonTerminal = paymentline.handlePaymentCancelResponse(false);
    expect(responseFailNonTerminal).toBe(false);
    expect(paymentline.payment_status).toBe("waitingScan");

    // Failed - Other
    card.payment_method_type = "other";
    paymentline.payment_status = "waitingCancel";
    const responseFailOther = paymentline.handlePaymentCancelResponse(false);
    expect(responseFailOther).toBe(false);
    expect(paymentline.payment_status).toBe("waiting");
});

test("forceDone", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    const data = { payment_status: "waiting" };
    const paymentline = createPaymentLine(store, order, card, data);

    paymentline.forceDone();
    expect(paymentline.payment_status).toBe("done");
});

test("forceCancel", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
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
    card.is_cash_count = true;
    card.payment_method_type = "none";
    expect(paymentline.canBeAdjusted()).toBe(false);

    // no payment interface + is bank qr code
    card.is_cash_count = false;
    card.payment_method_type = "bank_qr_code";
    expect(paymentline.canBeAdjusted()).toBe(false);

    // no payment interface + is not cash or bank qr code
    card.is_cash_count = false;
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
