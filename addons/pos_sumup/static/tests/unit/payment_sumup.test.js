import { test, expect, describe, beforeEach, waitUntil } from "@odoo/hoot";
import { advanceTime } from "@odoo/hoot-mock";
import { setupPosEnv, createPaymentLine, getFilledOrder } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { onRpc } from "@web/../tests/web_test_helpers";
import { patch } from "@web/core/utils/patch";
import {
    PaymentSumup,
    POLLING_INTERVAL_MS,
    POLLING_START_DELAY_MS,
} from "@pos_sumup/app/utils/payment/payment_sumup";

definePosModels();

let lastError = null;

beforeEach(() => {
    lastError = null;
    patch(PaymentSumup.prototype, {
        _notifySumupError(body) {
            lastError = body;
        },
    });
});

const setupSumup = async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const paymentMethod = store.models["pos.payment.method"].find(
        (pm) => pm.payment_provider === "sumup"
    );
    const sumup = paymentMethod.payment_interface;
    return { store, order, paymentMethod, sumup };
};

const notifyWebhook = (store, data) => {
    const channelInfo = store.data.channels.find((c) => c.channel === "SUMUP_LATEST_RESPONSE");
    channelInfo.method(data);
};

describe("sendPaymentRequest: payment", () => {
    test("resolves true when the webhook reports a successful payment", async () => {
        const { store, order, paymentMethod, sumup } = await setupSumup();
        const paymentLine = createPaymentLine(store, order, paymentMethod, {
            amount: 10,
            payment_status: "waiting",
        });

        onRpc("pos.payment.method", "sumup_pay", ({ args }) => {
            expect(args[0]).toEqual([paymentMethod.id]);
            expect(args[1]).toBe(10);
            return { data: { client_transaction_id: "ctid1", checkout_id: "chk1" } };
        });

        const result = sumup.sendPaymentRequest(paymentLine);
        await waitUntil(() => paymentLine.transaction_id === "ctid1");

        notifyWebhook(store, { client_transaction_id: "ctid1", status: "successful" });

        expect(await result).toBe(true);
        expect(lastError).toBe(null);
    });

    test("resolves false and shows an error when the webhook reports a failed payment", async () => {
        const { store, order, paymentMethod, sumup } = await setupSumup();
        const paymentLine = createPaymentLine(store, order, paymentMethod, {
            amount: 10,
            payment_status: "waiting",
        });

        onRpc("pos.payment.method", "sumup_pay", () => ({
            data: { client_transaction_id: "ctid1", checkout_id: "chk1" },
        }));

        const result = sumup.sendPaymentRequest(paymentLine);
        await waitUntil(() => paymentLine.transaction_id === "ctid1");
        notifyWebhook(store, {
            client_transaction_id: "ctid1",
            status: "failed",
            failure_reason: "Card declined",
        });

        expect(await result).toBe(false);
        expect(lastError).toBe("Card declined");
    });

    test("resolves false immediately when the sumup_pay RPC errors out", async () => {
        const { store, order, paymentMethod, sumup } = await setupSumup();
        const paymentLine = createPaymentLine(store, order, paymentMethod, {
            amount: 10,
            payment_status: "waiting",
        });

        onRpc("pos.payment.method", "sumup_pay", () => ({
            error: { message: "Could not reach SumUp." },
        }));

        const result = await sumup.sendPaymentRequest(paymentLine);

        expect(result).toBe(false);
        expect(lastError).toBe("Could not reach SumUp.");
    });

    test("falls back to polling the checkout status if the webhook is never received", async () => {
        const { store, order, paymentMethod, sumup } = await setupSumup();
        const paymentLine = createPaymentLine(store, order, paymentMethod, {
            amount: 10,
            payment_status: "waiting",
        });

        onRpc("pos.payment.method", "sumup_pay", () => ({
            data: { client_transaction_id: "ctid1", checkout_id: "chk1" },
        }));
        let checkoutStatusCalls = 0;
        onRpc("pos.payment.method", "sumup_get_checkout_status", ({ args }) => {
            checkoutStatusCalls++;
            expect(args[0]).toEqual([paymentMethod.id]);
            expect(args[1]).toBe("chk1");
            return { data: { status: "successful" } };
        });

        const result = sumup.sendPaymentRequest(paymentLine);
        await waitUntil(() => paymentLine.transaction_id === "ctid1");

        // Before the initial delay elapses, no poll should have happened yet.
        await advanceTime(POLLING_START_DELAY_MS - 1000);
        expect(checkoutStatusCalls).toBe(0);

        await advanceTime(1000 + POLLING_INTERVAL_MS);

        expect(await result).toBe(true);
    });

    test("stops polling once the webhook resolves the payment first", async () => {
        const { store, order, paymentMethod, sumup } = await setupSumup();
        const paymentLine = createPaymentLine(store, order, paymentMethod, {
            amount: 10,
            payment_status: "waiting",
        });

        onRpc("pos.payment.method", "sumup_pay", () => ({
            data: { client_transaction_id: "ctid1", checkout_id: "chk1" },
        }));
        let checkoutStatusCalls = 0;
        onRpc("pos.payment.method", "sumup_get_checkout_status", () => {
            checkoutStatusCalls++;
            return { data: { status: "successful" } };
        });

        const result = sumup.sendPaymentRequest(paymentLine);
        await waitUntil(() => paymentLine.transaction_id === "ctid1");
        notifyWebhook(store, { client_transaction_id: "ctid1", status: "successful" });
        expect(await result).toBe(true);

        // Well past the initial delay and several polling intervals: the timer
        // started by sendPaymentRequest must have been canceled by the webhook,
        // otherwise it would keep firing forever in the background.
        await advanceTime(POLLING_START_DELAY_MS + POLLING_INTERVAL_MS * 3);
        expect(checkoutStatusCalls).toBe(0);
    });
});

describe("sendPaymentRequest: refund", () => {
    test("sends the original transaction id and resolves true without waiting for a status", async () => {
        const { store, order, paymentMethod, sumup } = await setupSumup();
        const refundLine = createPaymentLine(store, order, paymentMethod, {
            amount: -10,
            transaction_id: "original_ctid",
        });

        onRpc("pos.payment.method", "sumup_refund", ({ args }) => {
            expect(args[0]).toEqual([paymentMethod.id]);
            expect(args[1]).toBe(-10);
            expect(args[2]).toBe("original_ctid");
            return { data: {} };
        });

        const result = await sumup.sendPaymentRequest(refundLine);

        expect(result).toBe(true);
        expect(lastError).toBe(null);
    });

    test("resolves false and shows an error when the refund RPC errors out", async () => {
        const { store, order, paymentMethod, sumup } = await setupSumup();
        const refundLine = createPaymentLine(store, order, paymentMethod, {
            amount: -10,
            transaction_id: "original_ctid",
        });

        onRpc("pos.payment.method", "sumup_refund", () => ({
            error: { message: "SumUp can't refund a transaction not paid with SumUp." },
        }));

        const result = await sumup.sendPaymentRequest(refundLine);

        expect(result).toBe(false);
        expect(lastError).toBe("SumUp can't refund a transaction not paid with SumUp.");
    });
});

describe("sendPaymentCancel", () => {
    test("sets the line back to retry and cancels any pending polling", async () => {
        const { store, order, paymentMethod, sumup } = await setupSumup();
        const paymentLine = createPaymentLine(store, order, paymentMethod, {
            amount: 10,
            payment_status: "waiting",
        });

        onRpc("pos.payment.method", "sumup_pay", () => ({
            data: { client_transaction_id: "ctid1", checkout_id: "chk1" },
        }));
        let checkoutStatusCalls = 0;
        onRpc("pos.payment.method", "sumup_get_checkout_status", () => {
            checkoutStatusCalls++;
            return { data: { status: "successful" } };
        });
        onRpc("pos.payment.method", "sumup_cancel", ({ args }) => {
            expect(args[0]).toEqual([paymentMethod.id]);
            return true;
        });

        sumup.sendPaymentRequest(paymentLine); // left pending on purpose, like a real cancel
        await waitUntil(() => paymentLine.transaction_id === "ctid1");

        const cancelled = await sumup.sendPaymentCancel(paymentLine);
        expect(cancelled).toBe(true);
        expect(paymentLine.getPaymentStatus()).toBe("retry");

        await advanceTime(POLLING_START_DELAY_MS + POLLING_INTERVAL_MS * 3);
        expect(checkoutStatusCalls).toBe(0);
    });
});
