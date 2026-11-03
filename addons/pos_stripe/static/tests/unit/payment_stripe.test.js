import { beforeEach, expect, test, waitUntil } from "@odoo/hoot";
import { mountWithCleanup, onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { getFilledOrder, setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { TipScreen } from "@point_of_sale/app/screens/tip_screen/tip_screen";
import { PaymentStripe } from "@pos_stripe/app/payment_stripe";

definePosModels();

let captures;
let errors;
let cardDetails;
let mcc;
let intentAmount;
let tip;
let skipTipping;

beforeEach(() => {
    captures = [];
    errors = [];
    cardDetails = { type: "card_present", card_present: { brand: "visa", network: "visa" } };
    mcc = "5812";
    tip = null;
    patchWithCleanup(PaymentStripe.prototype, {
        async createStripeTerminal() {
            this.terminal = {
                getConnectionStatus: () => "connected",
                collectPaymentMethod: async (secret, { config_override }) => {
                    skipTipping = config_override.skip_tipping;
                    return { paymentIntent: { id: "pi_1" } };
                },
                processPayment: async () => ({
                    paymentIntent: {
                        id: "pi_1",
                        amount: intentAmount + tip,
                        amount_details: { tip: { amount: tip } },
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
    onRpc("pos.payment.method", "stripe_payment_intent", ({ args }) => {
        intentAmount = Math.round(args[1] * 100);
        return { client_secret: "secret" };
    });
    onRpc("pos.payment.method", "stripe_capture_payment", ({ args, kwargs }) => {
        const rounding = kwargs.context?.stripe_currency_rounding;
        captures.push({ id: args[0], amount: kwargs.amount, rounding });
        return { id: args[0] };
    });
    onRpc("pos.payment.method", "stripe_account_mcc", () => mcc);
});

const payWithStripe = async ({ tipAfterPayment }) => {
    const store = await setupPosEnv();
    store.config.set_tip_after_payment = tipAfterPayment;
    store.connectedReader = "SIMULATOR";
    const order = await getFilledOrder(store);
    const method = store.models["pos.payment.method"].find(
        (pm) => pm.payment_provider === "stripe"
    );
    const line = order.addPaymentline(method).data;
    const result = await method.payment_interface.sendPaymentRequest(line);
    return { store, order, line, result };
};

const mountTipScreen = async (store, order) => {
    await store.syncAllOrders();
    store.config.tip_percentage_3 = 25;
    patchWithCleanup(TipScreen.prototype, { async printTipReceipt() {} });
    return mountWithCleanup(TipScreen, {
        props: { orderUuid: order.uuid, finalizeValidation: async () => {} },
    });
};

test("captures right after payment without tip after payment", async () => {
    const { line, result } = await payWithStripe({ tipAfterPayment: false });
    expect(result).toBe(true);
    expect(line.payment_status).toBe("done");
    expect(captures).toEqual([{ id: "pi_1", amount: undefined, rounding: undefined }]);
});

test("does not capture interac payments", async () => {
    cardDetails = { type: "interac_present", interac_present: { brand: "interac" } };
    const { line, result } = await payWithStripe({ tipAfterPayment: false });
    expect(result).toBe(true);
    expect(line.card_type).toBe("interac");
    expect(line.transaction_id).toBe("ch_1");
    expect(captures).toEqual([]);
});

test("defers the capture to the tip when overcapture is supported", async () => {
    cardDetails.card_present.overcapture_supported = true;
    const { line, result } = await payWithStripe({ tipAfterPayment: true });
    expect(result).toBe(true);
    expect(line.canBeAdjusted()).toBe(true);
    expect(captures).toEqual([]);
    expect(errors).toEqual([]);
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
    expect(captures).toEqual([{ id: "pi_1", amount: undefined, rounding: undefined }]);
    expect(order.is_tipped).toBe(true);
});

test("captures right away when overcapture is not supported", async () => {
    cardDetails.card_present.overcapture_supported = false;
    const { line, result } = await payWithStripe({ tipAfterPayment: true });
    expect(result).toBe(true);
    expect(line.payment_status).toBe("done");
    expect(line.canBeAdjusted()).toBe(false);
    expect(captures).toEqual([{ id: "pi_1", amount: undefined, rounding: undefined }]);
    expect(errors).toHaveLength(1);
    expect(errors[0].toString()).toInclude("merchant category code (MCC) is 5812.");
    expect(errors[0].toString()).toInclude(
        '<a href="https://docs.stripe.com/terminal/features/collecting-tips/on-receipt#availability" target="_blank">'
    );
});

test("mentions a missing MCC when overcapture is not supported", async () => {
    cardDetails.card_present.overcapture_supported = false;
    mcc = false;
    await payWithStripe({ tipAfterPayment: true });
    expect(errors).toHaveLength(1);
    expect(errors[0].toString()).toInclude("merchant category code (MCC) is not set.");
});

test("adds the tips entered on the terminal to the order", async () => {
    const store = await setupPosEnv();
    store.config.iface_tipproduct = true;
    store.connectedReader = "SIMULATOR";
    const order = await getFilledOrder(store);
    await store.setTip(1);
    const method = store.models["pos.payment.method"].find(
        (pm) => pm.payment_provider === "stripe"
    );
    const pay = async (terminalTip, amount) => {
        const line = order.addPaymentline(method).data;
        if (amount) {
            line.setAmount(amount);
        }
        const due = line.amount;
        tip = terminalTip;
        await method.payment_interface.sendPaymentRequest(line);
        return [due, line.amount];
    };
    expect(await pay(200, 10)).toEqual([10, 12]);
    expect(await pay(null, 5)).toEqual([5, 5]);
    const [due, amount] = await pay(350);
    expect(amount).toBe(due + 3.5);
    expect(skipTipping).toBe(false);
    const tipLines = order.lines.filter(
        (line) => line.product_id.id === store.config.tip_product_id.id
    );
    expect(tipLines.map((line) => line.price_unit)).toEqual([6.5]);
    expect(order.remainingDue).toBe(0);
});

test("skips tipping on the terminal when the order cannot take it", async () => {
    const store = await setupPosEnv();
    store.connectedReader = "SIMULATOR";
    const order = await getFilledOrder(store);
    const method = store.models["pos.payment.method"].find(
        (pm) => pm.payment_provider === "stripe"
    );
    const line = order.addPaymentline(method).data;
    const skipped = [];
    for (const config of [
        { iface_tipproduct: false },
        { iface_tipproduct: true, set_tip_after_payment: true },
        { set_tip_after_payment: false, self_ordering_mode: "kiosk" },
    ]) {
        Object.assign(store.config, config);
        await method.payment_interface.collectPayment(line.amount);
        skipped.push(skipTipping);
    }
    expect(skipped).toEqual([true, true, true]);
});
