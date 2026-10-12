import { expect, test, waitUntil } from "@odoo/hoot";
import { mountWithCleanup, onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { getFilledOrder, setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { TipScreen } from "@point_of_sale/app/screens/tip_screen/tip_screen";
import { PaymentStripe } from "@pos_stripe/app/payment_stripe";

definePosModels();

const payWithStripe = async ({ overcaptureSupported, mcc = "5812" }) => {
    const captures = [];
    const errors = [];
    patchWithCleanup(PaymentStripe.prototype, {
        createStripeTerminal() {
            const cardDetails = {
                type: "card_present",
                card_present: {
                    brand: "visa",
                    network: "visa",
                    overcapture_supported: overcaptureSupported,
                },
            };
            this.terminal = {
                getConnectionStatus: () => "connected",
                collectPaymentMethod: async () => ({ paymentIntent: { id: "pi_1" } }),
                processPayment: async () => ({
                    paymentIntent: {
                        id: "pi_1",
                        charges: { data: [{ id: "ch_1", payment_method_details: cardDetails }] },
                    },
                }),
            };
            return true;
        },
        _showError(msg) {
            errors.push(msg);
        },
    });
    onRpc("pos.payment.method", "stripe_payment_intent", () => ({ client_secret: "secret" }));
    onRpc("pos.payment.method", "stripe_capture_payment", ({ args }) => {
        captures.push(args[0]);
        return { id: args[0] };
    });
    onRpc("pos.payment.method", "stripe_account_mcc", () => mcc);

    const store = await setupPosEnv();
    store.config.set_tip_after_payment = true;
    store.connectedReader = "SIMULATOR";
    const order = await getFilledOrder(store);
    const method = store.models["pos.payment.method"].find(
        (pm) => pm.payment_provider === "stripe"
    );
    const line = order.addPaymentline(method).data;
    const result = await method.payment_interface.sendPaymentRequest(line);
    return { store, order, line, result, captures, errors };
};

test("defers the capture to the tip when overcapture is supported", async () => {
    const { line, result, captures, errors } = await payWithStripe({ overcaptureSupported: true });
    expect(result).toBe(true);
    expect(line.canBeAdjusted()).toBe(true);
    expect(captures).toEqual([]);
    expect(errors).toEqual([]);
});

test("captures after the tip", async () => {
    const { store, order, line, captures } = await payWithStripe({ overcaptureSupported: true });
    await store.syncAllOrders();
    store.config.tip_percentage_3 = 25;
    patchWithCleanup(TipScreen.prototype, { async printTipReceipt() {} });
    const screen = await mountWithCleanup(TipScreen, {
        props: { orderUuid: order.uuid, finalizeValidation: async () => {} },
    });
    // currency_id is related to the order on the server, which the mock server does not compute
    line.currency_id = store.currency;
    screen.state.inputTipAmount = "2";
    await screen.validateTip();
    await waitUntil(() => captures.length);
    expect(captures).toEqual(["pi_1"]);
});

test("captures right away when overcapture is not supported", async () => {
    const { line, result, captures, errors } = await payWithStripe({ overcaptureSupported: false });
    expect(result).toBe(true);
    expect(line.payment_status).toBe("done");
    expect(line.canBeAdjusted()).toBe(false);
    expect(captures).toEqual(["pi_1"]);
    expect(errors).toHaveLength(1);
    expect(errors[0].toString()).toInclude("merchant category code (MCC) is 5812.");
    expect(errors[0].toString()).toInclude(
        '<a href="https://docs.stripe.com/terminal/features/collecting-tips/on-receipt#availability" target="_blank">'
    );
});

test("mentions a missing MCC when overcapture is not supported", async () => {
    const { errors } = await payWithStripe({ overcaptureSupported: false, mcc: false });
    expect(errors).toHaveLength(1);
    expect(errors[0].toString()).toInclude("merchant category code (MCC) is not set.");
});
