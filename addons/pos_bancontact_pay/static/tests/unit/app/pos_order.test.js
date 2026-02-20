import { test, expect } from "@odoo/hoot";
import { setupPosEnv, getFilledOrder, createPaymentLine } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

test("canSendPaymentRequest", async () => {
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
    expect(order.canSendPaymentRequest({ paymentMethod: display })).toEqual(success);

    // One display payment not processing
    const paymentlineDisplay = createPaymentLine(store, order, display, {
        payment_status: "pending",
    });
    expect(order.canSendPaymentRequest({ paymentMethod: display })).toEqual(success);

    // One display payment processing
    paymentlineDisplay.payment_status = "waitingScan";
    expect(order.canSendPaymentRequest({ paymentMethod: display })).toEqual(success);

    // No sticker payment
    expect(order.canSendPaymentRequest({ paymentMethod: sticker1 })).toEqual(success);

    // One sticker payment not processing
    const paymentlineSticker = createPaymentLine(store, order, sticker1, {
        payment_status: "pending",
    });
    expect(order.canSendPaymentRequest({ paymentMethod: sticker1 })).toEqual(success);

    // One sticker payment processing
    paymentlineSticker.payment_status = "waitingScan";
    expect(order.canSendPaymentRequest({ paymentMethod: sticker1 })).toEqual(
        failureStickerAlreadyUsed
    );

    // Retry with the same paymentline
    expect(order.canSendPaymentRequest({ paymentline: paymentlineSticker })).toEqual(success);

    // Different sticker payment
    expect(order.canSendPaymentRequest({ paymentMethod: sticker2 })).toEqual(success);
});
