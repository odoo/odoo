import { test, expect } from "@odoo/hoot";
import { setupPosEnv, getFilledOrder, createPaymentLine } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

test("handlePaymentResponse", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const display = store.models["pos.payment.method"].get(4);
    const sticker = store.models["pos.payment.method"].get(5);

    const opts = { payment_status: "pending", qr_code: "http://example.com/qr" };
    const paymentlineDisplay = createPaymentLine(store, order, display, opts);
    const paymentlineSticker = createPaymentLine(store, order, sticker, opts);

    // Display failed payment
    const resDisplayFail = paymentlineDisplay.handlePaymentResponse(false);
    expect(resDisplayFail).toBe(false);
    expect(paymentlineDisplay.payment_status).toBe("retry");

    // Sticker failed payment
    const resStickerFail = paymentlineSticker.handlePaymentResponse(false);
    expect(resStickerFail).toBe(false);
    expect(paymentlineSticker.payment_status).toBe("retry");

    // Display successful payment
    const resDisplaySuccess = paymentlineDisplay.handlePaymentResponse(true);
    expect(resDisplaySuccess).toBe(false);
    expect(paymentlineDisplay.payment_status).toBe("waitingScan");

    // Sticker successful payment
    const resStickerSuccess = paymentlineSticker.handlePaymentResponse(true);
    expect(resStickerSuccess).toBe(false);
    expect(paymentlineSticker.payment_status).toBe("waitingScan");
});

test("forceDone", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const display = store.models["pos.payment.method"].get(4);

    const opts = { payment_status: "waitingScan", qr_code: "http://example.com/qr" };
    const paymentline = createPaymentLine(store, order, display, opts);

    paymentline.forceDone();
    expect(paymentline.payment_status).toBe("done");
    expect(paymentline.qr_code).toBeEmpty();
});

test("forceCancel", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const display = store.models["pos.payment.method"].get(4);

    const opts = {
        payment_status: "waitingScan",
        qr_code: "http://example.com/qr",
        bancontact_id: "bancontact_1",
    };
    const paymentline = createPaymentLine(store, order, display, opts);

    paymentline.forceCancel();
    expect(paymentline.payment_status).toBe("retry");
    expect(paymentline.bancontact_id).toBeEmpty();
    expect(paymentline.qr_code).toBeEmpty();
});
