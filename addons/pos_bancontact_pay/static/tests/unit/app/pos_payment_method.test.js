import { test, expect } from "@odoo/hoot";
import { setupPosEnv, getFilledOrder, createPaymentLine } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

test("_checkOrder", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const display = store.models["pos.payment.method"].get(4);
    const sticker1 = store.models["pos.payment.method"].get(5);
    const sticker2 = store.models["pos.payment.method"].get(6);

    const success = { status: true, message: "" };
    const failureStickerAlreadyUsed = {
        status: false,
        message: "This sticker is already processing another payment.",
    };

    // No display payment
    expect(display._checkOrder({ order })).toEqual(success);

    // One display payment not processing
    const paymentlineDisplay = createPaymentLine(store, order, display, {
        payment_status: "pending",
    });
    expect(display._checkOrder({ order })).toEqual(success);

    // One display payment processing
    paymentlineDisplay.payment_status = "waitingScan";
    expect(display._checkOrder({ order })).toEqual(success);

    // No sticker payment
    expect(sticker1._checkOrder({ order })).toEqual(success);

    // One sticker payment not processing
    const paymentlineSticker = createPaymentLine(store, order, sticker1, {
        payment_status: "pending",
    });
    expect(sticker1._checkOrder({ order })).toEqual(success);

    // One sticker payment processing
    paymentlineSticker.payment_status = "waitingScan";
    expect(sticker1._checkOrder({ order })).toEqual(failureStickerAlreadyUsed);

    // Retry with the same paymentline
    expect(sticker1._checkOrder({ order, paymentline: paymentlineSticker })).toEqual(success);

    // Different sticker payment
    expect(sticker2._checkOrder({ order })).toEqual(success);
});

test("getPaymentInterfaceStates", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const display = store.models["pos.payment.method"].get(4);
    const sticker = store.models["pos.payment.method"].get(5);

    display._checkOrder = () => ({ status: false, message: "dummy_error_display" });
    sticker._checkOrder = () => ({ status: false, message: "dummy_error_sticker" });

    const data = { payment_status: "pending" };
    const paymentline1 = createPaymentLine(store, order, display, data);
    const paymentline2 = createPaymentLine(store, order, sticker, data);

    // Display --> always allow
    expect(display.getPaymentInterfaceStates({ paymentline: paymentline1 })).toEqual({
        status: true,
        message: "",
    });

    // Sticker --> depends on _checkOrder
    expect(sticker.getPaymentInterfaceStates({ paymentline: paymentline2 })).toEqual({
        status: false,
        message: "dummy_error_sticker",
    });
});
