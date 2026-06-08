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
    expect(paymentlineDisplay.uiState.qrCode).toBeEmpty();

    // Sticker failed payment
    const resStickerFail = paymentlineSticker.handlePaymentResponse(false);
    expect(resStickerFail).toBe(false);
    expect(paymentlineSticker.payment_status).toBe("retry");
    expect(paymentlineSticker.uiState.qrCode).toBeEmpty();

    // Display successful payment
    const resDisplaySuccess = paymentlineDisplay.handlePaymentResponse(true);
    expect(resDisplaySuccess).toBe(false);
    expect(paymentlineDisplay.payment_status).toBe("waitingScan");
    expect(paymentlineDisplay.uiState.qrCode).toBe("http://example.com/qr");

    // Sticker successful payment
    const resStickerSuccess = paymentlineSticker.handlePaymentResponse(true);
    expect(resStickerSuccess).toBe(false);
    expect(paymentlineSticker.payment_status).toBe("waitingScan");
    expect(paymentlineSticker.uiState.qrCode).toBeEmpty();
});

test("handlePaymentCancelResponse", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const display = store.models["pos.payment.method"].get(4);

    const opts = { payment_status: "waitingScan", qr_code: "http://example.com/qr" };
    const paymentline = createPaymentLine(store, order, display, opts);
    paymentline.uiState.qrCode = "http://example.com/qr";

    // Failed cancellation
    const resCancelFail = paymentline.handlePaymentCancelResponse(false);
    expect(resCancelFail).toBe(false);
    expect(paymentline.uiState.qrCode).toBe("http://example.com/qr");

    // Successful cancellation
    const resCancelSuccess = paymentline.handlePaymentCancelResponse(true);
    expect(resCancelSuccess).toBe(true);
    expect(paymentline.uiState.qrCode).toBeEmpty();
});

test("forceDone", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const display = store.models["pos.payment.method"].get(4);

    const opts = { payment_status: "waitingScan", qr_code: "http://example.com/qr" };
    const paymentline = createPaymentLine(store, order, display, opts);
    paymentline.uiState.qrCode = "http://example.com/qr";

    paymentline.forceDone();
    expect(paymentline.payment_status).toBe("done");
    expect(paymentline.qr_code).toBeEmpty();
    expect(paymentline.uiState.qrCode).toBeEmpty();
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
    paymentline.uiState.qrCode = "http://example.com/qr";

    paymentline.forceCancel();
    expect(paymentline.payment_status).toBe("retry");
    expect(paymentline.bancontact_id).toBeEmpty();
    expect(paymentline.qr_code).toBeEmpty();
    expect(paymentline.uiState.qrCode).toBeEmpty();
});
