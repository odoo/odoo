import { test, expect, describe } from "@odoo/hoot";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv, getFilledOrder, createPaymentLine } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

describe("getBancontactErrorMessage", () => {
    test("EXPIRED", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        order.floating_order_name = "test_order";

        store.setOrder(null);
        const actualUnselectedOrder = store.getBancontactErrorMessage("EXPIRED", order);
        expect(actualUnselectedOrder).toBe("A payment for order test_order has expired.");

        store.setOrder(order);
        const actualCurrentOrder = store.getBancontactErrorMessage("EXPIRED", order);
        expect(actualCurrentOrder).toBe("Payment expired");
    });

    test("CANCELLED", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        order.floating_order_name = "test_order";

        store.setOrder(null);
        const actualUnselectedOrder = store.getBancontactErrorMessage("CANCELLED", order);
        expect(actualUnselectedOrder).toBe("A payment for order test_order was cancelled.");

        store.setOrder(order);
        const actualCurrentOrder = store.getBancontactErrorMessage("CANCELLED", order);
        expect(actualCurrentOrder).toBe("Payment cancelled");
    });

    test("OTHER", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        order.floating_order_name = "test_order";

        store.setOrder(null);
        const actualUnselectedOrder = store.getBancontactErrorMessage(
            "AUTHORIZATION_FAILED",
            order
        );
        expect(actualUnselectedOrder).toBe("A payment for order test_order has failed.");

        store.setOrder(order);
        const actualCurrentOrder = store.getBancontactErrorMessage("AUTHORIZATION_FAILED", order);
        expect(actualCurrentOrder).toBe("Payment failed");
    });
});

describe("handleBancontactPayNotification", () => {
    test("SUCCEEDED", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        const display = store.models["pos.payment.method"].get(4);

        const data = { payment_status: "waitingScan" };
        const paymentline = createPaymentLine(store, order, display, data);

        // Prepare asserts
        order.floating_order_name = "test_order_1";
        store.autoValidateOrder = () => {
            expect.step("store.autoValidateOrder");
        };

        let notificationMessage = "";
        patchWithCleanup(store.data, { read() {} });
        patchWithCleanup(store.notification, {
            add(message) {
                notificationMessage = message;
            },
        });

        const reset = (orderSelected, paymentlineSelected, id) => {
            notificationMessage = null;
            paymentline.uiState.qrCode = "test_qr_code";
            store.setOrder(orderSelected);
            orderSelected.selectPaymentline(paymentlineSelected);
            store.qrCode = {
                paymentline: paymentlineSelected,
                closer: () => {
                    expect.step(`store.qrCode.closer.${id}`);
                },
            };
            store.autoValidateOrder = () => {
                expect.step(`store.autoValidateOrder.${id}`);
            };
        };

        // Current order + current qr code displayed + current payment line
        reset(order, paymentline, 1);
        await store.handleBancontactPayNotification({
            payment_id: paymentline.id,
            bancontact_status: "SUCCEEDED",
        });

        expect(notificationMessage).toBe(null);
        expect(store.qrCode).toBe(null);
        expect(paymentline.uiState.qrCode).toBe(null);
        expect.verifySteps(["store.qrCode.closer.1", "store.autoValidateOrder.1"]);

        // Current order + current qr code displayed + different payment line
        const paymentline2 = createPaymentLine(store, order, display, data);
        reset(order, paymentline2, 2);
        store.qrCode.paymentline = paymentline;
        await store.handleBancontactPayNotification({
            payment_id: paymentline.id,
            bancontact_status: "SUCCEEDED",
        });

        expect(notificationMessage).toBe("Payment received");
        expect(store.qrCode).toBe(null);
        expect(paymentline.uiState.qrCode).toBe(null);
        expect.verifySteps(["store.qrCode.closer.2", "store.autoValidateOrder.2"]);

        // Current order + different qr code displayed + current payment line
        reset(order, paymentline, 3);
        store.qrCode.paymentline = paymentline2;
        await store.handleBancontactPayNotification({
            payment_id: paymentline.id,
            bancontact_status: "SUCCEEDED",
        });

        expect(notificationMessage).toBe(null);
        expect(store.qrCode).not.toBe(null);
        expect(paymentline.uiState.qrCode).toBe(null);
        expect.verifySteps(["store.autoValidateOrder.3"]);

        // Current order + different qr code displayed + different payment line
        reset(order, paymentline2, 4);
        await store.handleBancontactPayNotification({
            payment_id: paymentline.id,
            bancontact_status: "SUCCEEDED",
        });

        expect(notificationMessage).toBe("Payment received");
        expect(store.qrCode).not.toBe(null);
        expect(paymentline.uiState.qrCode).toBe(null);
        expect.verifySteps(["store.autoValidateOrder.4"]);

        // Other order selected - Fully paid
        order.toBeValidate = () => true;
        const order2 = await getFilledOrder(store);
        const paymentline3 = createPaymentLine(store, order2, display, data);
        reset(order2, paymentline3, 5);
        await store.handleBancontactPayNotification({
            payment_id: paymentline.id,
            bancontact_status: "SUCCEEDED",
        });

        expect(notificationMessage).toInclude(`The order test_order_1 has been fully paid.`);
        expect(store.qrCode).not.toBe(null);
        expect(paymentline.uiState.qrCode).toBe(null);
        expect.verifySteps([]);

        // Other order selected - Partially paid
        order.toBeValidate = () => false;
        reset(order2, paymentline3, 6);
        await store.handleBancontactPayNotification({
            payment_id: paymentline.id,
            bancontact_status: "SUCCEEDED",
        });

        expect(notificationMessage).toInclude(`The order test_order_1 has been partially paid.`);
        expect(store.qrCode).not.toBe(null);
        expect(paymentline.uiState.qrCode).toBe(null);
        expect.verifySteps([]);
    });

    test("FAILED", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        const display = store.models["pos.payment.method"].get(4);

        const data = { payment_status: "waitingScan" };
        const paymentline = createPaymentLine(store, order, display, data);

        // Prepare asserts
        order.floating_order_name = "test_order_1";
        store.autoValidateOrder = () => {
            expect.step("store.autoValidateOrder");
        };

        let notificationMessage = "";
        patchWithCleanup(store.data, { read() {} });
        patchWithCleanup(store.notification, {
            add(message) {
                notificationMessage = message;
            },
        });

        const reset = (orderSelected, paymentlineSelected, id) => {
            notificationMessage = null;
            paymentline.uiState.qrCode = "test_qr_code";
            store.setOrder(orderSelected);
            store.qrCode = {
                paymentline: paymentlineSelected,
                closer: () => {
                    expect.step(`store.qrCode.closer.${id}`);
                },
            };
        };

        // Current order and current payment line
        reset(order, paymentline, 1);
        await store.handleBancontactPayNotification({
            payment_id: paymentline.id,
            bancontact_status: "FAILED",
        });

        expect(notificationMessage).toBe("Payment failed");
        expect(store.qrCode).toBe(null);
        expect(paymentline.uiState.qrCode).toBe(null);
        expect.verifySteps(["store.qrCode.closer.1"]);

        // Current order but different payment line selected
        const paymentline2 = createPaymentLine(store, order, display, data);
        reset(order, paymentline2, 2);
        await store.handleBancontactPayNotification({
            payment_id: paymentline.id,
            bancontact_status: "FAILED",
        });

        expect(notificationMessage).toBe("Payment failed");
        expect(store.qrCode).not.toBe(null);
        expect(paymentline.uiState.qrCode).toBe(null);
        expect.verifySteps([]);

        // Other order selected
        const order2 = await getFilledOrder(store);
        const paymentline3 = createPaymentLine(store, order2, display, data);
        reset(order2, paymentline3, 3);
        await store.handleBancontactPayNotification({
            payment_id: paymentline.id,
            bancontact_status: "FAILED",
        });

        expect(notificationMessage).toBe(`A payment for order test_order_1 has failed.`);
        expect(store.qrCode).not.toBe(null);
        expect(paymentline.uiState.qrCode).toBe(null);
        expect.verifySteps([]);
    });
});

test("canSendPaymentRequest", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const display = store.models["pos.payment.method"].get(4);
    const sticker = store.models["pos.payment.method"].get(5);

    const data = { payment_status: "pending" };
    const paymentline1 = createPaymentLine(store, order, display, data);
    const paymentline2 = createPaymentLine(store, order, sticker, data);
    order.canSendPaymentRequest = () => ({ status: false, message: "dummy_error" });

    // Display --> always allow
    expect(store.canSendPaymentRequest({ paymentline: paymentline1 })).toEqual({
        status: true,
        message: "",
    });

    // Sticker --> depends on order
    expect(store.canSendPaymentRequest({ paymentline: paymentline2 })).toEqual({
        status: false,
        message: "dummy_error",
    });
});
