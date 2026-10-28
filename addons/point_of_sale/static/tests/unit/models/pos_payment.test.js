import { describe, expect, freezeTime, mockDate, test } from "@odoo/hoot";
import { definePosModels } from "../data/generate_model_definitions";
import {
    createOrderWithPrice,
    createPaymentLine,
    getFilledOrder,
    setupMultiCurrency,
    setupPosEnv,
} from "../utils";

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
    card.type = "cash";
    card.payment_method_type = "none";
    expect(paymentline.canBeAdjusted()).toBe(false);

    // no payment interface + is bank qr code
    card.type = "bank";
    card.payment_method_type = "bank_qr_code";
    expect(paymentline.canBeAdjusted()).toBe(false);

    // no payment interface + is not cash or bank qr code
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

describe("setAmount", () => {
    // 1 Ⓐ = 15 $, see setupMultiCurrency
    const setup = async () => {
        const store = await setupPosEnv();
        const { xta } = setupMultiCurrency(store);
        const order = await createOrderWithPrice(store, 136.57);
        const card = store.models["pos.payment.method"].get(2);
        return { store, order, card, xta };
    };

    test("in the POS currency", async () => {
        const { store, order, card } = await setup();
        const line = createPaymentLine(store, order, card, { amount: 0 });

        line.setAmount("12.344");
        expect(line.amount).toBe(12.34);
        expect(line.amount_currency).toBe(12.34);

        line.setAmount("abc");
        expect(line.amount).toBe(0);
        expect(line.amount_currency).toBe(0);
    });

    test("in the POS currency on a foreign currency line", async () => {
        const { store, order, card, xta } = await setup();
        const line = createPaymentLine(store, order, card, {
            amount: 0,
            foreign_currency_id: xta.id,
        });

        line.setAmount(30);
        expect(line.amount).toBe(30);
        expect(line.amount_currency).toBe(2);
    });

    test("in a foreign currency", async () => {
        const { store, order, card, xta } = await setup();
        const line = createPaymentLine(store, order, card, {
            amount: 0,
            foreign_currency_id: xta.id,
        });

        line.setAmount("2.344", xta);
        expect(line.amount_currency).toBe(2.34);
        expect(line.amount).toBe(35.1);

        line.setAmount("abc", xta);
        expect(line.amount_currency).toBe(0);
        expect(line.amount).toBe(0);
    });

    test("in a foreign currency, settling the order books the amount left to pay", async () => {
        const { store, order, card, xta } = await setup();
        const line = createPaymentLine(store, order, card, {
            amount: 0,
            foreign_currency_id: xta.id,
        });

        // Not enough: converted amount
        line.setAmount(9.09, xta);
        expect(line.amount).toBe(136.35);

        // Exactly the 9.10 Ⓐ due: 136.50 $ converted, booked as the 136.57 $ due
        line.setAmount(9.1, xta);
        expect(line.amount).toBe(136.57);
        expect(order.amountPaid).toBe(136.57);

        // Too much: converted amount, the rest is change
        line.setAmount(9.11, xta);
        expect(line.amount).toBe(136.65);
        expect(order.change).toBe(-0.08);
    });

    test("in a foreign currency, settling the order after other lines", async () => {
        const { store, order, card, xta } = await setup();
        createPaymentLine(store, order, card, { amount: 100 });
        const line = createPaymentLine(store, order, card, {
            amount: 0,
            foreign_currency_id: xta.id,
        });

        // Not enough: 36.57 $ left = 2.438 Ⓐ, rounded to 2.44 Ⓐ
        line.setAmount(2.43, xta);
        expect(line.amount).toBe(36.45);

        // Exactly the 2.44 Ⓐ due: 36.60 $ converted, booked as the 36.57 $ due
        line.setAmount(2.44, xta);
        expect(line.amount).toBe(36.57);
        expect(order.amountPaid).toBe(136.57);
        expect(order.change).toBe(0);
    });
});
