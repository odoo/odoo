import { expect, test } from "@odoo/hoot";
import { advanceTime } from "@odoo/hoot-mock";
import { getFilledOrder, setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { onRpc } from "@web/../tests/web_test_helpers";
import {
    CARD_PAYMENT_TIMEOUT,
    POLLING_INTERVAL_MS,
} from "@pos_adyen/app/utils/payment/payment_adyen";

definePosModels();

const adyenNotification = (serviceId, result = "Success") => ({
    SaleToPOIResponse: {
        MessageHeader: { ServiceID: serviceId },
        PaymentResponse: {
            PaymentReceipt: [],
            PaymentResult: { AmountsResp: { TipAmount: 0 } },
            Response: {
                AdditionalResponse: "pspReference=PSP123",
                Result: result,
            },
        },
    },
});

const setupAdyen = async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const paymentMethod = store.models["pos.payment.method"].find(
        (pm) => pm.use_payment_terminal === "adyen"
    );
    const adyen = paymentMethod.payment_terminal;
    const paymentLine = order.addPaymentline(paymentMethod).data;
    paymentLine.setPaymentStatus("waitingCard");
    return { adyen, paymentLine };
};

test("a payment line waiting for the terminal times out if nothing ever answers", async () => {
    const { adyen, paymentLine } = await setupAdyen();

    const result = adyen.waitForPaymentConfirmation();
    await advanceTime(CARD_PAYMENT_TIMEOUT);

    await expect(result).resolves.toBe(false);
    expect(paymentLine.getPaymentStatus()).toBe("timeout");
});

test("the timeout does not overwrite a status already settled by a real response", async () => {
    const { adyen, paymentLine } = await setupAdyen();

    const result = adyen.waitForPaymentConfirmation();
    // Simulate handleAdyenStatusResponse() settling the line before the
    // timeout fires (e.g. a late but valid Adyen notification comes in).
    paymentLine.setPaymentStatus("done");
    await advanceTime(CARD_PAYMENT_TIMEOUT);

    await expect(result).resolves.toBe(false);
    expect(paymentLine.getPaymentStatus()).toBe("done");
});

test("polling picks up the result if the webhook never arrives", async () => {
    const { adyen, paymentLine } = await setupAdyen();
    paymentLine.setTerminalServiceId("service-123");
    onRpc("pos.payment.method", "get_latest_adyen_status", () => adyenNotification("service-123"));

    const result = adyen.waitForPaymentConfirmation();
    await advanceTime(POLLING_INTERVAL_MS);

    await expect(result).resolves.toBe(true);
    expect(paymentLine.transaction_id).toBe("PSP123");
});

test("polling ignores a notification for a different service id", async () => {
    const { adyen, paymentLine } = await setupAdyen();
    paymentLine.setTerminalServiceId("service-123");
    onRpc("pos.payment.method", "get_latest_adyen_status", () =>
        adyenNotification("unrelated-service-id")
    );

    const result = adyen.waitForPaymentConfirmation();
    await advanceTime(CARD_PAYMENT_TIMEOUT);

    await expect(result).resolves.toBe(false);
    expect(paymentLine.getPaymentStatus()).toBe("timeout");
    expect(paymentLine.transaction_id).toBe(undefined);
});

test("stops polling once the webhook resolves the payment first", async () => {
    const { adyen, paymentLine } = await setupAdyen();
    paymentLine.setTerminalServiceId("service-456");
    let pollCount = 0;
    onRpc("pos.payment.method", "get_latest_adyen_status", () => {
        pollCount++;
        return adyenNotification("service-456");
    });

    const result = adyen.waitForPaymentConfirmation();
    // The webhook wins the race, before any poll tick has a chance to run.
    await adyen.handleAdyenStatusResponse();
    const countRightAfterWebhook = pollCount;

    await advanceTime(POLLING_INTERVAL_MS * 3);

    await expect(result).resolves.toBe(true);
    expect(pollCount).toBe(countRightAfterWebhook);
});
