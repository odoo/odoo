import { test, expect } from "@odoo/hoot";
import { setupPosEnv, getFilledOrder, createPaymentLine } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

test("getPaymentInterfaceStates", async () => {
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
    expect(display.getPaymentInterfaceStates({ order })).toEqual(success);

    // One display payment not processing
    const paymentlineDisplay = createPaymentLine(store, order, display, {
        payment_status: "pending",
    });
    expect(display.getPaymentInterfaceStates({ order })).toEqual(success);

    // One display payment processing
    paymentlineDisplay.payment_status = "waitingScan";
    expect(display.getPaymentInterfaceStates({ order })).toEqual(success);

    // No sticker payment
    expect(sticker1.getPaymentInterfaceStates({ order })).toEqual(success);

    // One sticker payment not processing
    const paymentlineSticker = createPaymentLine(store, order, sticker1, {
        payment_status: "pending",
    });
    expect(sticker1.getPaymentInterfaceStates({ order })).toEqual(success);

    // One sticker payment processing
    paymentlineSticker.payment_status = "waitingScan";
    expect(sticker1.getPaymentInterfaceStates({ order })).toEqual(failureStickerAlreadyUsed);

    // Retry with the same paymentline
    expect(sticker1.getPaymentInterfaceStates({ order, paymentline: paymentlineSticker })).toEqual(
        success
    );

    // Different sticker payment
    expect(sticker2.getPaymentInterfaceStates({ order })).toEqual(success);
});
