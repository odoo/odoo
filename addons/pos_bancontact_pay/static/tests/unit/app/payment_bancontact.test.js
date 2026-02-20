import { test, expect, describe, animationFrame } from "@odoo/hoot";
import {
    setupPosEnv,
    getFilledOrder,
    createPaymentLine,
    activateMountingDialogs,
} from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { click } from "@odoo/hoot-dom";

definePosModels();

describe("sendPaymentRequest", () => {
    test("failed to create bancontact payment", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        const display = store.models["pos.payment.method"].get(4);
        const sticker = store.models["pos.payment.method"].get(5);

        const opts = { amount: -1, payment_status: "waiting" };
        const paymentlineDisplay = createPaymentLine(store, order, display, opts);
        const paymentlineSticker = createPaymentLine(store, order, sticker, opts);
        const paymentlines = [paymentlineDisplay, paymentlineSticker];

        for (const paymentline of paymentlines) {
            let failed = false;
            try {
                await paymentline.payment_interface.sendPaymentRequest(paymentline);
            } catch {
                failed = true;
            }

            expect(failed).toBe(true);
            expect(paymentline.bancontact_id).toBeEmpty();
            expect(paymentline.qr_code).toBeEmpty();
            expect(store.qrCode).toBeEmpty();

            // The payment status will be updated by `handlePaymentResponse`
            expect(paymentline.payment_status).toBe("waiting");
        }
    });

    test("success to create bancontact payment", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        const display = store.models["pos.payment.method"].get(4);
        const sticker = store.models["pos.payment.method"].get(5);

        const opts = { payment_status: "waiting" };
        const paymentlineDisplay = createPaymentLine(store, order, display, opts);
        const paymentlineSticker = createPaymentLine(store, order, sticker, opts);
        const paymentlines = [paymentlineDisplay, paymentlineSticker];

        store.displayQrCode = () => {
            expect.step("store.displayQrCode");
        };
        for (const paymentline of paymentlines) {
            const result = await paymentline.payment_interface.sendPaymentRequest(paymentline);
            const bancontactId = "bancontact_" + paymentline.id;
            const qrCodeUrl = `https://example.com/qrcode/${bancontactId}`;

            expect(result).toBe(true);
            expect(paymentline.bancontact_id).toBe(bancontactId);
            expect(paymentline.qr_code).toBe(qrCodeUrl);

            expect.verifySteps(
                paymentline.payment_method_id.bancontact_usage === "display"
                    ? ["store.displayQrCode"]
                    : []
            );

            // The payment status will be updated by `handlePaymentResponse`
            expect(paymentline.payment_status).toBe("waiting");
        }
    });
});

describe("sendPaymentCancel", () => {
    test("failed to cancel bancontact payment (ERR: 400)", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        const display = store.models["pos.payment.method"].get(4);
        const sticker = store.models["pos.payment.method"].get(5);

        const opts = (bancontact_id) => ({
            amount: -400, // To trigger ERR: 400
            payment_status: "waitingCancel",
            bancontact_id: bancontact_id,
            qr_code: `https://example.com/qrcode/${bancontact_id}`,
        });
        const displayTestId = "bancontact_1";
        const stickerTestId = "bancontact_2";
        const paymentlineDisplay = createPaymentLine(store, order, display, opts(displayTestId));
        const paymentlineSticker = createPaymentLine(store, order, sticker, opts(stickerTestId));
        const paymentlines = [paymentlineDisplay, paymentlineSticker];

        for (const paymentline of paymentlines) {
            const result = await paymentline.payment_interface.sendPaymentCancel(paymentline);
            expect(result).toBe(true);
            expect(paymentline.bancontact_id).toBeEmpty();
            expect(paymentline.qr_code).toBeEmpty();

            // The payment status is updated by `forceCancel`
            expect(paymentline.payment_status).toBe("retry");
        }
    });

    test("failed to cancel bancontact payment (ERR: 422)", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        const display = store.models["pos.payment.method"].get(4);
        const sticker = store.models["pos.payment.method"].get(5);

        const opts = (bancontact_id) => ({
            amount: -422, // To trigger ERR: 422
            payment_status: "waitingCancel",
            bancontact_id: bancontact_id,
            qr_code: `https://example.com/qrcode/${bancontact_id}`,
        });
        const displayTestId = "bancontact_1";
        const stickerTestId = "bancontact_2";
        const paymentlineDisplay = createPaymentLine(store, order, display, opts(displayTestId));
        const paymentlineSticker = createPaymentLine(store, order, sticker, opts(stickerTestId));
        const paymentlines = [paymentlineDisplay, paymentlineSticker];
        const getBancontactId = (pl) =>
            pl.id === paymentlineDisplay.id ? displayTestId : stickerTestId;
        const qrCodeUrl = (pl) =>
            pl.id === paymentlineDisplay.id
                ? `https://example.com/qrcode/${displayTestId}`
                : `https://example.com/qrcode/${stickerTestId}`;

        await activateMountingDialogs(store.env);
        for (const paymentline of paymentlines) {
            // ---- Click on 'Close' button ----
            const promiseResultClose = paymentline.payment_interface.sendPaymentCancel(paymentline);

            await animationFrame();
            await click(".modal-footer .btn-primary");

            const resultClose = await promiseResultClose;
            expect(resultClose).toBe(false);
            expect(paymentline.bancontact_id).toBe(getBancontactId(paymentline));
            expect(paymentline.qr_code).toBe(qrCodeUrl(paymentline));

            // The payment status will be updated by `handlePaymentResponse`
            expect(paymentline.payment_status).toBe("waitingCancel");

            // ---- Force cancel ----
            const promiseResultForce = paymentline.payment_interface.sendPaymentCancel(paymentline);

            await animationFrame();
            await click(".modal-footer .btn-secondary");

            const resultForce = await promiseResultForce;
            expect(resultForce).toBe(true);
            expect(paymentline.bancontact_id).toBeEmpty();
            expect(paymentline.qr_code).toBeEmpty();

            // The payment status is updated by `forceCancel`
            expect(paymentline.payment_status).toBe("retry");
        }
    });

    test("success to cancel bancontact payment", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        const display = store.models["pos.payment.method"].get(4);
        const sticker = store.models["pos.payment.method"].get(5);

        const opts = (bancontact_id) => ({
            payment_status: "waitingCancel",
            bancontact_id: bancontact_id,
            qr_code: `https://example.com/qrcode/${bancontact_id}`,
        });
        const displayTestId = "bancontact_1";
        const stickerTestId = "bancontact_2";
        const paymentlineDisplay = createPaymentLine(store, order, display, opts(displayTestId));
        const paymentlineSticker = createPaymentLine(store, order, sticker, opts(stickerTestId));
        const paymentlines = [paymentlineDisplay, paymentlineSticker];

        for (const paymentline of paymentlines) {
            const result = await paymentline.payment_interface.sendPaymentCancel(paymentline);
            expect(result).toBe(true);
            expect(paymentline.bancontact_id).toBeEmpty();
            expect(paymentline.qr_code).toBeEmpty();

            // The payment status will be updated by `handlePaymentResponse`
            expect(paymentline.payment_status).toBe("waitingCancel");
        }
    });
});
