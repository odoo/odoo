import { test, expect, describe } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv, getFilledOrder } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

definePosModels();

describe("payment_screen.js", () => {
    describe("processExternalQRPayment", () => {
        test("Failed to create payment", async () => {
            const store = await setupPosEnv();
            const order = await getFilledOrder(store);

            const paymentMethodDisplay = store.models["pos.payment.method"].get(4);
            const paymentMethodSticker = store.models["pos.payment.method"].get(5);

            const paymentScreen = await mountWithCleanup(PaymentScreen, {
                props: { orderUuid: order.uuid },
            });
            const commonVals = {
                payment_status: "pending",
                pos_order_id: order.id,
                amount: -1, // <-- Invalid amount to trigger failure
            };
            const paymentLineDisplay = store.models["pos.payment"].create({
                ...commonVals,
                payment_method_id: paymentMethodDisplay.id,
            });
            const paymentLineSticker = store.models["pos.payment"].create({
                ...commonVals,
                payment_method_id: paymentMethodSticker.id,
            });

            for (const line of [paymentLineDisplay, paymentLineSticker]) {
                const actual = await paymentScreen.processExternalQRPayment(line);
                expect(actual).toBe(false); // Always false because the bus will handle the result
                expect(line.payment_status).toBe("pending");
            }
        });

        test("Success to create payment", async () => {
            const store = await setupPosEnv();
            const order = await getFilledOrder(store);

            const paymentMethodDisplay = store.models["pos.payment.method"].get(4);
            const paymentMethodSticker = store.models["pos.payment.method"].get(5);

            const paymentScreen = await mountWithCleanup(PaymentScreen, {
                props: { orderUuid: order.uuid },
            });
            const commonVals = {
                payment_status: "pending",
                pos_order_id: order.id,
                amount: 10,
            };
            const paymentLineDisplay = store.models["pos.payment"].create({
                ...commonVals,
                payment_method_id: paymentMethodDisplay.id,
            });
            const paymentLineSticker = store.models["pos.payment"].create({
                ...commonVals,
                payment_method_id: paymentMethodSticker.id,
            });

            for (const line of [paymentLineDisplay, paymentLineSticker]) {
                const actual = await paymentScreen.processExternalQRPayment(line);
                expect(actual).toBe(false); // Always false because the bus will handle the result
                expect(line.payconiq_id).toBe("azertyuiop");
                expect(line.qr_code).toBe("https://example.com/qrcode/azertyuiop");
                expect(line.payment_status).toBe("waitingScanExternalQR");

                if (line.payment_method_id.isExternalDisplayQR) {
                    const actual = {
                        ...line.qrPaymentData,
                        close: typeof line.qrPaymentData.close,
                    };
                    const expected = {
                        qrCode: "https://example.com/qrcode/azertyuiop",
                        name: "Payconiq Display",
                        amount: "$\u00A010.00",
                        close: "function",
                    };
                    expect(actual).toEqual(expected);
                } else if (line.payment_method_id.isExternalStickerQR) {
                    const actual = store.stickerPaymentsInProgress.has(line.payment_method_id.id);
                    expect(actual).toBe(true);
                }
            }
        });
    });

    describe("sendPaymentCancel", () => {
        test("Failed to cancel payment", async () => {
            const store = await setupPosEnv();
            const order = await getFilledOrder(store);

            const paymentMethodDisplay = store.models["pos.payment.method"].get(4);
            const paymentMethodSticker = store.models["pos.payment.method"].get(5);

            const paymentScreen = await mountWithCleanup(PaymentScreen, {
                props: { orderUuid: order.uuid },
            });
            const commonVals = {
                pos_order_id: order.id,
                amount: 10,
                payment_status: "waitingScanExternalQR",
                payconiq_id: "failed",
                qr_code: "https://example.com/qrcode/failed",
            };
            const paymentLineDisplay = store.models["pos.payment"].create({
                ...commonVals,
                payment_method_id: paymentMethodDisplay.id,
            });
            const paymentLineSticker = store.models["pos.payment"].create({
                ...commonVals,
                payment_method_id: paymentMethodSticker.id,
            });

            for (const line of [paymentLineDisplay, paymentLineSticker]) {
                store.paymentTerminalInProgress = true;
                line.qrPaymentData = {
                    qrCode: line.qr_code,
                    name: line.payment_method_id.name,
                    amount: "$\u00A010.00",
                    close: () => {},
                };
                store.stickerPaymentsInProgress.add(line.payment_method_id.id);

                await paymentScreen.sendPaymentCancel(line);
                expect(line.payment_status).toBe("retry");
                expect(store.paymentTerminalInProgress).toBe(false);
                expect(line.qrPaymentData).toBeEmpty();
                expect(store.stickerPaymentsInProgress.has(line.payment_method_id.id)).toBe(false);
            }
        });

        test("Success to cancel payment", async () => {
            const store = await setupPosEnv();
            const order = await getFilledOrder(store);

            const paymentMethodDisplay = store.models["pos.payment.method"].get(4);
            const paymentMethodSticker = store.models["pos.payment.method"].get(5);

            const paymentScreen = await mountWithCleanup(PaymentScreen, {
                props: { orderUuid: order.uuid },
            });
            const commonVals = {
                pos_order_id: order.id,
                amount: 10,
                payment_status: "waitingScanExternalQR",
                payconiq_id: "azertyuiop",
                qr_code: "https://example.com/qrcode/azertyuiop",
            };
            const paymentLineDisplay = store.models["pos.payment"].create({
                ...commonVals,
                payment_method_id: paymentMethodDisplay.id,
            });
            const paymentLineSticker = store.models["pos.payment"].create({
                ...commonVals,
                payment_method_id: paymentMethodSticker.id,
            });

            for (const line of [paymentLineDisplay, paymentLineSticker]) {
                store.paymentTerminalInProgress = true;
                line.qrPaymentData = {
                    qrCode: line.qr_code,
                    name: line.payment_method_id.name,
                    amount: "$\u00A010.00",
                    close: () => {},
                };
                store.stickerPaymentsInProgress.add(line.payment_method_id.id);

                await paymentScreen.sendPaymentCancel(line);

                expect(line.payment_status).toBe("retry");
                expect(store.paymentTerminalInProgress).toBe(false);
                expect(line.qrPaymentData).toBeEmpty();
                expect(store.stickerPaymentsInProgress.has(line.payment_method_id.id)).toBe(false);
            }
        });
    });

    describe("Bus pos_sync_payconiq", () => {
        test("IDENTIFIED", async () => {
            const store = await setupPosEnv();
            const order = await getFilledOrder(store);

            const paymentMethodDisplay = store.models["pos.payment.method"].get(4);
            const paymentMethodSticker = store.models["pos.payment.method"].get(5);

            const paymentScreen = await mountWithCleanup(PaymentScreen, {
                props: { orderUuid: order.uuid },
            });
            const commonVals = {
                pos_order_id: order.id,
                amount: 10,
                payment_status: "waitingScanExternalQR",
                payconiq_id: "azertyuiop",
                qr_code: "https://example.com/qrcode/azertyuiop",
            };
            const paymentLineDisplay = store.models["pos.payment"].create({
                ...commonVals,
                payment_method_id: paymentMethodDisplay.id,
            });
            const paymentLineSticker = store.models["pos.payment"].create({
                ...commonVals,
                payment_method_id: paymentMethodSticker.id,
            });

            for (const line of [paymentLineDisplay, paymentLineSticker]) {
                store.paymentTerminalInProgress = true;
                line.qrPaymentData = {
                    qrCode: line.qr_code,
                    name: line.payment_method_id.name,
                    amount: "$\u00A010.00",
                    close: () => {},
                };
                store.stickerPaymentsInProgress.add(line.payment_method_id.id);

                await paymentScreen._onPayconiqSync({ status: "IDENTIFIED", uuid: line.uuid });

                expect(line.payment_status).toBe("waitingPaymentExternalQR");
                expect(store.paymentTerminalInProgress).toBe(true);
                expect({
                    ...line.qrPaymentData,
                    close: typeof line.qrPaymentData.close,
                }).toEqual({
                    qrCode: "https://example.com/qrcode/azertyuiop",
                    name: line.payment_method_id.name,
                    close: "function",
                    amount: "$\u00A010.00",
                });
                expect(store.stickerPaymentsInProgress.has(line.payment_method_id.id)).toBe(true);
            }
        });

        test("IDENTIFIED - wrong previous status", async () => {
            const store = await setupPosEnv();
            const order = await getFilledOrder(store);

            const paymentMethodDisplay = store.models["pos.payment.method"].get(4);
            const paymentMethodSticker = store.models["pos.payment.method"].get(5);

            const paymentScreen = await mountWithCleanup(PaymentScreen, {
                props: { orderUuid: order.uuid },
            });
            const commonVals = {
                pos_order_id: order.id,
                amount: 10,
                payment_status: "done", // <-- Wrong previous status
                payconiq_id: "azertyuiop",
                qr_code: "https://example.com/qrcode/azertyuiop",
            };
            const paymentLineDisplay = store.models["pos.payment"].create({
                ...commonVals,
                payment_method_id: paymentMethodDisplay.id,
            });
            const paymentLineSticker = store.models["pos.payment"].create({
                ...commonVals,
                payment_method_id: paymentMethodSticker.id,
            });

            for (const line of [paymentLineDisplay, paymentLineSticker]) {
                store.paymentTerminalInProgress = true;
                line.qrPaymentData = {
                    qrCode: line.qr_code,
                    name: line.payment_method_id.name,
                    amount: "$\u00A010.00",
                    close: () => {},
                };
                store.stickerPaymentsInProgress.add(line.payment_method_id.id);

                await paymentScreen._onPayconiqSync({ status: "IDENTIFIED", uuid: line.uuid });

                expect(line.payment_status).toBe("done"); // Unchanged
                expect(store.paymentTerminalInProgress).toBe(true);
                expect({
                    ...line.qrPaymentData,
                    close: typeof line.qrPaymentData.close,
                }).toEqual({
                    qrCode: "https://example.com/qrcode/azertyuiop",
                    name: line.payment_method_id.name,
                    close: "function",
                    amount: "$\u00A010.00",
                });
                expect(store.stickerPaymentsInProgress.has(line.payment_method_id.id)).toBe(true);
            }
        });

        test("SUCCEEDED", async () => {
            const store = await setupPosEnv();
            const order = store.addNewOrder();

            const product = store.models["product.product"].get(5);
            const paymentMethodDisplay = store.models["pos.payment.method"].get(4);
            const paymentMethodSticker = store.models["pos.payment.method"].get(5);

            await store.addLineToCurrentOrder(
                {
                    product_id: product,
                    product_tmpl_id: product.product_tmpl_id,
                    price_unit: 20,
                    qty: 1,
                    tax_ids: [],
                },
                {}
            );
            const paymentScreen = await mountWithCleanup(PaymentScreen, {
                props: { orderUuid: order.uuid },
            });
            const commonVals = {
                pos_order_id: order.id,
                payment_status: "waitingPaymentExternalQR",
                payconiq_id: "azertyuiop",
                qr_code: "https://example.com/qrcode/azertyuiop",
            };
            const paymentLineDisplay = store.models["pos.payment"].create({
                ...commonVals,
                amount: 5,
                payment_method_id: paymentMethodDisplay.id,
            });
            const paymentLineSticker = store.models["pos.payment"].create({
                ...commonVals,
                amount: order.amount_total - 5, // Pay the rest with the sticker method
                payment_method_id: paymentMethodSticker.id,
            });

            const lines = [paymentLineDisplay, paymentLineSticker];
            for (let i = 0; i < lines.length; i++) {
                const isLast = i === lines.length - 1;
                const line = lines[i];

                store.paymentTerminalInProgress = true;
                line.qrPaymentData = {
                    qrCode: line.qr_code,
                    name: line.payment_method_id.name,
                    amount: "$\u00A010.00",
                    close: () => {},
                };
                store.stickerPaymentsInProgress.add(line.payment_method_id.id);

                await paymentScreen._onPayconiqSync({ status: "SUCCEEDED", uuid: line.uuid });
                await new Promise((resolve) => setTimeout(resolve, 200)); // Wait for the validate order (async)

                expect(line.payment_status).toBe("done");
                expect(store.paymentTerminalInProgress).toBe(false);
                expect(line.qrPaymentData).toBeEmpty();
                expect(store.stickerPaymentsInProgress.has(line.payment_method_id.id)).toBe(false);
                expect(paymentScreen.currentOrder.state).toBe(isLast ? "paid" : "draft");
            }
        });

        test("FAILED", async () => {
            const store = await setupPosEnv();
            const order = await getFilledOrder(store);

            const paymentMethodDisplay = store.models["pos.payment.method"].get(4);
            const paymentMethodSticker = store.models["pos.payment.method"].get(5);

            const paymentScreen = await mountWithCleanup(PaymentScreen, {
                props: { orderUuid: order.uuid },
            });

            const commonVals = {
                pos_order_id: order.id,
                amount: 10,
                payment_status: "waitingScanExternalQR",
                payconiq_id: "azertyuiop",
                qr_code: "https://example.com/qrcode/azertyuiop",
            };
            const paymentLineDisplay = store.models["pos.payment"].create({
                ...commonVals,
                payment_method_id: paymentMethodDisplay.id,
            });
            const paymentLineSticker = store.models["pos.payment"].create({
                ...commonVals,
                payment_method_id: paymentMethodSticker.id,
            });

            for (const line of [paymentLineDisplay, paymentLineSticker]) {
                store.paymentTerminalInProgress = true;
                line.qrPaymentData = {
                    qrCode: line.qr_code,
                    name: line.payment_method_id.name,
                    amount: "$\u00A010.00",
                    close: () => {},
                };
                store.stickerPaymentsInProgress.add(line.payment_method_id.id);

                await paymentScreen._onPayconiqSync({ status: "FAILED", uuid: line.uuid });

                expect(line.payment_status).toBe("retry");
                expect(store.paymentTerminalInProgress).toBe(false);
                expect(line.qrPaymentData).toBeEmpty();
                expect(store.stickerPaymentsInProgress.has(line.payment_method_id.id)).toBe(false);
            }
        });
    });
});
