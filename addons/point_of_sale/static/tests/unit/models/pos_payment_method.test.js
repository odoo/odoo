import { test, expect } from "@odoo/hoot";
import { getFilledOrder, setupPosEnv, createPaymentLine } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";

definePosModels();

test("_checkOrder", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card1 = store.models["pos.payment.method"].get(2);
    const card2 = store.models["pos.payment.method"].create({ ...card1, id: 1004, name: "Card 2" });
    card1.payment_method_type = "card_type_1";
    card2.payment_method_type = "card_type_2";

    const success = { status: true, message: "" };
    const failure = {
        status: false,
        message: "There is already an electronic payment in progress.",
    };

    // No existing processing payment
    expect(card1._checkOrder({ order })).toEqual(success);

    // Same type but already processing
    const paymentline = createPaymentLine(store, order, card1);
    paymentline.payment_status = "waitingCard";
    expect(card1._checkOrder({ order })).toEqual(failure);

    // Can send the request while processing if it's the same payment line
    expect(card1._checkOrder({ order, paymentline })).toEqual(success);

    // Same type but none processing
    paymentline.payment_status = "pending";
    expect(card1._checkOrder({ order })).toEqual(success);
});

test("getPaymentInterfaceStates", async () => {
    const store = await setupPosEnv();
    await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);

    // Order 1: no payment lines --> Ignored
    const result1 = card.getPaymentInterfaceStates();
    expect(result1).toEqual({ status: true, message: "" });

    // Order 2: has a paymentline and _checkOrder returns success
    card._checkOrder = () => ({ status: true, message: "" });
    const order2 = await getFilledOrder(store);
    createPaymentLine(store, order2, card);
    const result2 = card.getPaymentInterfaceStates();
    expect(result2).toEqual({ status: true, message: "" });

    // Order 3: has a paymentline and _checkOrder returns failure
    card._checkOrder = () => ({ status: false, message: "Test Message" });
    const order3 = await getFilledOrder(store);
    createPaymentLine(store, order3, card);
    const result3 = card.getPaymentInterfaceStates();
    expect(result3).toEqual({ status: false, message: "Test Message" });
});
