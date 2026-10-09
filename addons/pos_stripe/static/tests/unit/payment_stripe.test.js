import { beforeEach, expect, test, waitUntil } from "@odoo/hoot";
import { mountWithCleanup, onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { getFilledOrder, setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { TipScreen } from "@point_of_sale/app/screens/tip_screen/tip_screen";
import { PaymentStripe } from "@pos_stripe/app/payment_stripe";

definePosModels();

let captures;
let cardDetails;

beforeEach(() => {
    captures = [];
    cardDetails = { type: "card_present", card_present: { brand: "visa", network: "visa" } };
    patchWithCleanup(PaymentStripe.prototype, {
        async createStripeTerminal() {
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
    });
    onRpc("pos.payment.method", "stripe_payment_intent", () => ({ client_secret: "secret" }));
    onRpc("pos.payment.method", "stripe_capture_payment", ({ args, kwargs }) => {
        const rounding = kwargs.context.stripe_currency_rounding;
        captures.push({ id: args[0], amount: kwargs.amount, rounding });
        return { id: args[0] };
    });
});

const payWithStripe = async ({ tipAfterPayment }) => {
    const store = await setupPosEnv();
    store.config.set_tip_after_payment = tipAfterPayment;
    store.connectedReader = "SIMULATOR";
    const order = await getFilledOrder(store);
    const method = store.models["pos.payment.method"].find(
        (pm) => pm.use_payment_terminal === "stripe"
    );
    const line = order.addPaymentline(method).data;
    const result = await method.payment_terminal.sendPaymentRequest(line.uuid);
    return { store, order, line, result };
};

const mountTipScreen = async (store, order) => {
    await store.syncAllOrders();
    patchWithCleanup(TipScreen.prototype, { async printTipReceipt() {} });
    return mountWithCleanup(TipScreen, { props: { orderUuid: order.uuid } });
};

test("captures right after payment without tip after payment", async () => {
    const { line, result } = await payWithStripe({ tipAfterPayment: false });
    expect(result).toBe(true);
    expect(line.payment_status).toBe("done");
    expect(captures).toEqual([{ id: "pi_1", amount: null, rounding: undefined }]);
});

test("does not capture interac payments", async () => {
    cardDetails = { type: "interac_present", interac_present: { brand: "interac" } };
    const { line, result } = await payWithStripe({ tipAfterPayment: false });
    expect(result).toBe(true);
    expect(line.card_type).toBe("interac");
    expect(line.transaction_id).toBe("ch_1");
    expect(captures).toEqual([]);
});

test("defers the capture to the tip when tip after payment is set", async () => {
    const { line, result } = await payWithStripe({ tipAfterPayment: true });
    expect(result).toBe(true);
    expect(line.canBeAdjusted()).toBe(true);
    expect(captures).toEqual([]);
});

test("captures the tip with the payment", async () => {
    const { store, order, line } = await payWithStripe({ tipAfterPayment: true });
    const amount = line.amount;
    const screen = await mountTipScreen(store, order);
    // currency_id is related to the order on the server, which the mock server does not compute
    line.currency_id = store.currency;
    screen.state.inputTipAmount = "2";
    await screen.validateTip();
    await waitUntil(() => captures.length);
    expect(captures).toEqual([
        {
            id: "pi_1",
            amount: amount + 2,
            rounding: store.currency.rounding,
        },
    ]);
});

test("captures the payment when no tip is given", async () => {
    const { store, order } = await payWithStripe({ tipAfterPayment: true });
    const screen = await mountTipScreen(store, order);
    screen.state.inputTipAmount = "";
    await screen.validateTip();
    expect(captures).toEqual([{ id: "pi_1", amount: null, rounding: undefined }]);
    expect(order.is_tipped).toBe(true);
});
