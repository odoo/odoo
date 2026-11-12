import { expect, freezeTime, mockDate, test, waitUntil } from "@odoo/hoot";
import { definePosModels } from "../data/generate_model_definitions";
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
    // We have only sent the cancel, it is not confirmed yet, status remains unchanged.
    expect(paymentline.payment_status).toBe("waitingCancel");

    // Failed - Terminal
    card.payment_method_type = "terminal";
    paymentline.payment_status = "waitingCancel";
    const responseFailTerminal = paymentline.handlePaymentCancelResponse(false);
    expect(responseFailTerminal).toBe(false);
    expect(paymentline.payment_status).toBe("waitingCard");

    // Failed - Cash machine
    card.payment_method_type = "cash_machine";
    paymentline.payment_status = "waitingCancel";
    const responseFailCashMachine = paymentline.handlePaymentCancelResponse(false);
    expect(responseFailCashMachine).toBe(false);
    expect(paymentline.payment_status).toBe("waitingCard");

    // Failed - External QR
    card.payment_method_type = "qr";
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
    card.type = "cash";
    card.payment_interface = false;
    expect(paymentline.canBeAdjusted()).toBe(false);

    // no payment interface + is not cash
    card.type = "bank";
    expect(paymentline.canBeAdjusted()).toBe(true);

    // payment interface payment that supports adjustments
    card.payment_interface = "fakePaymentInterface";
    paymentline.payment_method_metadata = { can_be_adjusted: true };
    expect(paymentline.canBeAdjusted()).toBe(true);

    // payment interface payment that does not support adjustments
    card.payment_interface = "fakePaymentInterface";
    paymentline.payment_method_metadata = {};
    expect(paymentline.canBeAdjusted()).toBe(false);
});

test("requiresCapture", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    const paymentline = createPaymentLine(store, order, card);

    // no payment interface
    card.payment_interface = false;
    expect(paymentline.requiresCapture()).toBe(false);

    // regular payment interface payment -> does not require capturing
    card.payment_interface = "fakePaymentInterface";
    paymentline.payment_method_metadata = {};
    expect(paymentline.requiresCapture()).toBe(false);

    // payment interface payment that can be adjusted -> does require capturing
    card.payment_interface = "fakePaymentInterface";
    paymentline.payment_method_metadata = { can_be_adjusted: true };
    expect(paymentline.requiresCapture()).toBe(true);

    // payment interface payment that cannot be adjusted but requires capture
    card.payment_interface = "fakePaymentInterface";
    paymentline.payment_method_metadata = { can_be_adjusted: false, requires_capture: true };
    expect(paymentline.requiresCapture()).toBe(true);
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
        adjustPayment: (_amount, _currency, _transactionId, _extraArgs, callback) =>
            callback({ status: "paid" }),
    };
    await paymentline.adjustAmount(20);
    expect(paymentline.getAmount()).toBe(30);
});

test("setAmount: config currency differs from company currency", async () => {
    // Company in USD, Sales Journal (hence config and order) in EUR at 0.87
    const store = await setupPosEnv();
    const usd = store.models["res.currency"].get(1);
    const eur = store.models["res.currency"].get(125);
    store.config.currency_id = eur;
    const cash = store.models["pos.payment.method"].get(1);
    cash.currency_ids = [usd, eur];
    const order = await getFilledOrder(store);
    expect(order.totalDue).toBe(595);

    expect(eur.convert(595)).toBe(595);
    expect(usd.convert(595)).toBe(683.91);

    const eurLine = createPaymentLine(store, order, cash, { foreign_currency_id: eur });
    eurLine.setAmount(595);
    expect(eurLine.amount).toBe(595);
    expect(eurLine.amount_currency).toBe(595);

    const usdLine = createPaymentLine(store, order, cash, { foreign_currency_id: usd });
    usdLine.setAmount(683.91, usd);
    expect(usdLine.amount).toBe(595);
    expect(usdLine.amount_currency).toBe(683.91);
});

test("getRefundedPayment", async () => {
    const store = await setupPosEnv();
    const originalOrder = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    const originalPayment = createPaymentLine(store, originalOrder, card);
    const refundedOrder = await getFilledOrder(store, { refunded_order_id: originalOrder.id });
    const refundPayment = createPaymentLine(store, refundedOrder, card, { amount: -10 });

    expect(refundPayment.getRefundedPayment()).toBe(originalPayment);
});

test("pay", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    const paymentline = createPaymentLine(store, order, card);
    let finishStartPayment,
        finishPayment = null;

    card.payment_method_type = "terminal";
    card.payment_interface = {
        startPayment: async (_amount, _currency, _extraArgs, callback) => {
            await new Promise((resolve) => (finishStartPayment = resolve));
            finishPayment = () => callback({ transaction_id: "abc", status: "paid" });
            return { status: "pending", transaction_id: "abc" };
        },
    };

    const payPromise = paymentline.pay();

    // Immediately the status is set to 'waiting'
    expect(paymentline.getPaymentStatus()).toBe("waiting");

    // Once startPayment returns, the status is set to 'waitingCard'
    finishStartPayment();
    await waitUntil(() => paymentline.getPaymentStatus() === "waitingCard");
    expect(paymentline.transaction_id).toBe("abc");

    // When the payment is confirmed, the status is set to 'done'
    finishPayment();
    await payPromise;
    expect(paymentline.getPaymentStatus()).toBe("done");
});

test("pay: qr code", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    const paymentline = createPaymentLine(store, order, card);

    card.payment_method_type = "qr";
    card.payment_interface = {
        startPayment: async () => ({ status: "pending", transaction_id: "abc", qr_code: "12345" }),
    };

    await paymentline.pay();

    expect(paymentline.getPaymentStatus()).toBe("waitingScan");
    expect(paymentline.qr_code.startsWith("data:image")).toBe(true);
});

test("resumePayment", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    const paymentline = createPaymentLine(store, order, card);

    paymentline.transaction_id = "abc";
    card.payment_interface = {
        startListening: async (transactionId, callback) => {
            callback({ transaction_id: transactionId, status: "paid" });
        },
    };

    const result = await paymentline.resumePayment();
    expect(result).toEqual({ transaction_id: "abc", status: "paid" });
});
