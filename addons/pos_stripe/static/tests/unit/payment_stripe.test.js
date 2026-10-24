import { expect, test } from "@odoo/hoot";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { createPaymentLine, getFilledOrder, setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { PaymentStripe } from "@pos_stripe/app/payment_stripe";

definePosModels();

const getInterface = async () => {
    patchWithCleanup(PaymentStripe.prototype, { createStripeTerminal() {} });
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const pm = store.models["pos.payment.method"].get(2);
    pm.payment_provider = "stripe";
    const line = createPaymentLine(store, order, pm);
    return { store, line, iface: new PaymentStripe(store, pm) };
};

test("a captured payment stores the card brand", async () => {
    const { line, iface } = await getInterface();
    iface.capturePayment = async () => ({
        id: "stripe-capture",
        charges: { data: [{ payment_method_details: { card_present: { brand: "visa" } } }] },
    });

    await iface.captureAfterPayment({ paymentIntent: { id: "stripe-intent" } }, line);
    expect(line.card_brand).toBe("visa");
    expect(line.card_type).toBeEmpty();
});

test("an interac payment cannot be adjusted", async () => {
    const { store, line, iface } = await getInterface();
    store.config.set_tip_after_payment = true;

    expect(iface.canBeAdjusted(line.uuid)).toBe(true);
    line.card_brand = "interac";
    expect(iface.canBeAdjusted(line.uuid)).toBe(false);
});
