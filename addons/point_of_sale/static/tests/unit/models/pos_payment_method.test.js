import { test, expect } from "@odoo/hoot";
import { getFilledOrder, setupPosEnv, createPaymentLine } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";

definePosModels();

test("isBlockedBy", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card1 = store.models["pos.payment.method"].get(2);
    const card2 = store.models["pos.payment.method"].create({ ...card1, id: 1004, name: "Card 2" });
    const cash = store.models["pos.payment.method"].create({ ...card1, id: 1005, name: "Cash" });
    card1.payment_method_type = "card_type_1";
    card2.payment_method_type = "card_type_2";
    cash.payment_method_type = "none";

    const line1 = createPaymentLine(store, order, card1);
    const lineNone = createPaymentLine(store, order, cash);

    // Same type
    expect(card1.isBlockedBy(line1, { order })).toBe(true);
    // Other type
    expect(card2.isBlockedBy(line1, { order })).toBe(false);
    // Lines of type none never block
    expect(cash.isBlockedBy(lineNone, { order })).toBe(false);
});

test("canStartPayment", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    card.payment_method_type = "provider";

    const success = { status: true, message: "" };
    const failure = {
        status: false,
        message: "There is already an electronic payment in progress.",
    };

    // No payment interface: never blocked
    card.payment_interface = null;
    expect(card.canStartPayment({ order })).toEqual(success);
    card.payment_interface = {};

    // No processing payment
    expect(card.canStartPayment({ order })).toEqual(success);

    // Processing on this order
    const paymentline = createPaymentLine(store, order, card);
    paymentline.payment_status = "waiting_card";
    expect(card.canStartPayment({ order })).toEqual(failure);

    // Processing on another open order
    const order2 = await getFilledOrder(store);
    expect(card.canStartPayment({ order: order2 })).toEqual(failure);

    // Can send the request while processing if it's the same payment line
    expect(card.canStartPayment({ order, paymentline })).toEqual(success);

    // Not processing
    paymentline.payment_status = "pending";
    expect(card.canStartPayment({ order })).toEqual(success);

    // The hooks decide for each processing line and give the message
    paymentline.payment_status = "waiting_card";
    card.getBlockingMessage = () => "Test Message";
    expect(card.canStartPayment({ order })).toEqual({ status: false, message: "Test Message" });
    card.isBlockedBy = () => false;
    expect(card.canStartPayment({ order })).toEqual(success);
});

test("paymentInterfaceKey", async () => {
    const store = await setupPosEnv();
    const card = store.models["pos.payment.method"].get(2);

    // No provider
    expect(card.paymentInterfaceKey).toBe(false);

    // Provider
    card.payment_provider = "adyen";
    card.payment_method_type = "provider";
    expect(card.paymentInterfaceKey).toBe("adyen");

    // Bank transfer methods have no provider: the key is their type
    card.payment_provider = false;
    card.payment_method_type = "bank_transfer";
    expect(card.paymentInterfaceKey).toBe("bank_transfer");
});
