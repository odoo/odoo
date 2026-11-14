import { advanceTime, waitUntil, expect, test, beforeEach } from "@odoo/hoot";
import { getFilledOrder, setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { PaymentWorldline } from "@pos_worldline/app/payment_worldline";

definePosModels();

const fakeTransactionId = "fakeTransactionId";
let lastError = null;

beforeEach(() => {
    lastError = null;
    patchWithCleanup(PaymentWorldline.prototype, {
        _showWorldlineError(error) {
            lastError = this._extractErrorMessage(error);
        },
    });
});

const setupWorldline = async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const paymentMethod = store.models["pos.payment.method"].find(
        (pm) => pm.use_payment_terminal === "worldline_api"
    );
    const worldline = paymentMethod.payment_terminal;
    const paymentLine = order.addPaymentline(paymentMethod).data;

    const mockWorldlineCreateTransactionWithResult = (result) => {
        onRpc("pos.payment.method", "worldline_create_transaction", ({ args }) => {
            expect(args[0]).toEqual([paymentMethod.id]);
            expect(args[1]).toBe("CardPayment");
            expect(args[2]).toBe(17.85);
            expect(args[3]).toBe(paymentLine.uuid);
            expect(args[4]).toBe(order.session_id.id);
            return result;
        });
    };

    return { worldline, paymentLine, mockWorldlineCreateTransactionWithResult };
};

test("successful payment", async () => {
    const { worldline, paymentLine, mockWorldlineCreateTransactionWithResult } =
        await setupWorldline();
    mockWorldlineCreateTransactionWithResult({});

    const result = worldline.sendPaymentRequest(paymentLine.uuid);
    await waitUntil(() => paymentLine.payment_status === "waitingCard");
    worldline.handleWorldlineStatusResponse(paymentLine, {
        transaction_id: fakeTransactionId,
        success: true,
    });

    await expect(result).resolves.toBe(true);
    expect(lastError).toBe(null);
    expect(paymentLine.transaction_id).toBe(fakeTransactionId);
});

test("shows error when the transaction request fails", async () => {
    const { worldline, paymentLine, mockWorldlineCreateTransactionWithResult } =
        await setupWorldline();
    mockWorldlineCreateTransactionWithResult({ error: "Terminal unreachable" });

    const result = await worldline.sendPaymentRequest(paymentLine.uuid);

    expect(result).toBe(false);
    expect(lastError).toBe("Terminal unreachable");
});

test("shows error on declined payment", async () => {
    const { worldline, paymentLine, mockWorldlineCreateTransactionWithResult } =
        await setupWorldline();
    mockWorldlineCreateTransactionWithResult({});

    const result = worldline.sendPaymentRequest(paymentLine.uuid);
    await waitUntil(() => paymentLine.payment_status === "waitingCard");
    worldline.handleWorldlineStatusResponse(paymentLine, {
        transaction_id: fakeTransactionId,
        success: false,
    });

    await expect(result).resolves.toBe(false);
    expect(lastError).toBe("The transaction was declined or failed. Please try again.");
});

test("sends an unreferenced refund for a negative payment line", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store, {}, false, true);
    const paymentMethod = store.models["pos.payment.method"].find(
        (pm) => pm.use_payment_terminal === "worldline_api"
    );
    const worldline = paymentMethod.payment_terminal;
    const paymentLine = order.addPaymentline(paymentMethod).data;
    onRpc("pos.payment.method", "worldline_create_transaction", ({ args }) => {
        expect(args[1]).toBe("Refund");
        expect(args[2]).toBe(Math.abs(paymentLine.amount));
        expect(args).toHaveLength(5);
        return {};
    });

    const result = worldline.sendPaymentRequest(paymentLine.uuid);
    await waitUntil(() => paymentLine.payment_status === "waitingCard");
    worldline.handleWorldlineStatusResponse(paymentLine, {
        transaction_id: fakeTransactionId,
        success: true,
    });

    await expect(result).resolves.toBe(true);
    expect(lastError).toBe(null);
});

const startPaymentToCancel = async () => {
    const { worldline, paymentLine, mockWorldlineCreateTransactionWithResult } =
        await setupWorldline();
    mockWorldlineCreateTransactionWithResult({ exchange_id: "exchange-id" });
    onRpc("pos.payment.method", "worldline_cancel_transaction", () => ({}));
    const payment = worldline.sendPaymentRequest(paymentLine.uuid);
    await waitUntil(() => paymentLine.payment_status === "waitingCard");
    let cancelSettled = false;
    const cancel = worldline
        .sendPaymentCancel(paymentLine.pos_order_id, paymentLine.uuid)
        .finally(() => (cancelSettled = true));
    await waitUntil(() => worldline.cancelResolvers[paymentLine.uuid]);
    return { worldline, paymentLine, payment, cancel, isCancelSettled: () => cancelSettled };
};

test("cancellation waits for the webhook to report the aborted transaction", async () => {
    const { worldline, paymentLine, payment, cancel, isCancelSettled } =
        await startPaymentToCancel();
    expect(isCancelSettled()).toBe(false);

    worldline.handleWorldlineStatusResponse(paymentLine, {
        success: false,
        error: "Transaction was cancelled on the terminal. Please try again.",
    });

    await expect(cancel).resolves.toBe(true);
    await expect(payment).resolves.toBe(false);
    expect(lastError).toBe(null);
});

test("status polling resumes after a page refresh", async () => {
    const { worldline, paymentLine } = await setupWorldline();
    onRpc("pos.payment.method", "worldline_get_transaction_status", ({ args }) => {
        expect(args[1]).toBe("exchange-id");
        return { status: "done", success: true, transaction_id: fakeTransactionId };
    });
    // State restored from IndexedDB after a refresh, with no in-memory resolver.
    paymentLine.uiState.worldlineExchangeId = "exchange-id";
    paymentLine.setPaymentStatus("waitingCard");

    worldline._resumePendingTransactions();
    await advanceTime(5000);

    await waitUntil(() => paymentLine.payment_status === "done");
    expect(paymentLine.transaction_id).toBe(fakeTransactionId);
    expect(lastError).toBe(null);
});
