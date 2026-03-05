import { test, describe, expect } from "@odoo/hoot";
import { mountWithCleanup, onRpc } from "@web/../tests/web_test_helpers";
import { PaymentPage } from "@pos_self_order/app/pages/payment_page/payment_page";
import { setupSelfPosEnv, getFilledSelfOrder } from "../utils";
import { definePosSelfModels } from "../data/generate_model_definitions";
import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";
import { advanceTime } from "@odoo/hoot-mock";

definePosSelfModels();

class MockPaymentInterface extends PaymentInterface {
    setup() {
        this.hasBeenCalled = false;
    }
    sendPaymentRequest(line) {
        this.hasBeenCalled = true;
        if (line.useQr) {
            line.qr_code = "mock_qr_code";
            return false;
        }
        return true;
    }
}

class MockPaymentInterfaceWithError extends MockPaymentInterface {
    sendPaymentRequest(line) {
        this.hasBeenCalled = true;
        if (line.useQr) {
            throw new Error("Payment failed");
        }
        return false;
    }
}

const setupPaymentPage = async () => {
    const store = await setupSelfPosEnv();

    const paymentNoProvider = store.models["pos.payment.method"].create({
        payment_provider: null,
        payment_method_type: "none",
    });

    const paymentTerminal = store.models["pos.payment.method"].create({
        payment_provider: "mock_terminal",
        payment_method_type: "terminal",
    });
    paymentTerminal.payment_interface = new MockPaymentInterface();

    const paymentTerminalWithError = store.models["pos.payment.method"].create({
        payment_provider: "mock_terminal",
        payment_method_type: "terminal",
    });
    paymentTerminalWithError.payment_interface = new MockPaymentInterfaceWithError();

    const paymentExternalQr = store.models["pos.payment.method"].create({
        payment_provider: "mock_qr",
        payment_method_type: "external_qr",
    });
    paymentExternalQr.payment_interface = new MockPaymentInterface();

    const paymentExternalQrWithError = store.models["pos.payment.method"].create({
        payment_provider: "mock_qr",
        payment_method_type: "external_qr",
    });
    paymentExternalQrWithError.payment_interface = new MockPaymentInterfaceWithError();

    await getFilledSelfOrder(store);
    const paymentPage = await mountWithCleanup(PaymentPage, {});

    return {
        paymentPage,
        store,
        paymentNoProvider,
        paymentTerminal,
        paymentTerminalWithError,
        paymentExternalQr,
        paymentExternalQrWithError,
    };
};

describe("startPayment", () => {
    test("succeeds if the backend returns no error", async () => {
        const { paymentPage, store, paymentNoProvider } = await setupPaymentPage();
        paymentPage.state.paymentMethodId = paymentNoProvider.id;

        onRpc("/kiosk/payment/1/kiosk", () => true);
        await paymentPage.startPayment();

        expect(store.paymentError).toBe(false);
    });

    test("fails if the backend returns an error", async () => {
        const { paymentPage, store, paymentNoProvider } = await setupPaymentPage();
        paymentPage.state.paymentMethodId = paymentNoProvider.id;

        onRpc("/kiosk/payment/1/kiosk", () => {
            throw new Error();
        });
        await paymentPage.startPayment();

        expect(store.paymentError).toBe(true);
    });

    test("succeeds if the payment terminal succeeds and backend returns no error", async () => {
        const { paymentPage, store, paymentTerminal } = await setupPaymentPage();
        paymentPage.state.paymentMethodId = paymentTerminal.id;

        onRpc("/kiosk/payment/1/kiosk", () => true);
        await paymentPage.startPayment();

        expect(paymentTerminal.payment_interface.hasBeenCalled).toBe(true);
        expect(store.paymentError).toBe(false);
    });

    test("fails if the payment terminal fails", async () => {
        const { paymentPage, store, paymentTerminalWithError } = await setupPaymentPage();
        paymentPage.state.paymentMethodId = paymentTerminalWithError.id;

        onRpc("/kiosk/payment/1/kiosk", () => true);
        await paymentPage.startPayment();

        expect(paymentTerminalWithError.payment_interface.hasBeenCalled).toBe(true);
        expect(store.paymentError).toBe(true);
    });

    test("fails if the payment terminal succeeds but the backend returns an error", async () => {
        const { paymentPage, store, paymentTerminal } = await setupPaymentPage();
        paymentPage.state.paymentMethodId = paymentTerminal.id;

        onRpc("/kiosk/payment/1/kiosk", () => {
            throw new Error();
        });
        await paymentPage.startPayment();

        expect(paymentTerminal.payment_interface.hasBeenCalled).toBe(true);
        expect(store.paymentError).toBe(true);
    });

    test("succeeds if the external QR code payment interface succeeds and backend returns no error", async () => {
        const { paymentPage, store, paymentExternalQr } = await setupPaymentPage();
        paymentPage.state.paymentMethodId = paymentExternalQr.id;

        await paymentPage.startPayment();

        expect(paymentExternalQr.payment_interface.hasBeenCalled).toBe(true);
        expect(store.paymentError).toBe(false);
        await advanceTime(500); // Wait timeout fade out
        expect(paymentPage.state.qrCode).toBe("mock_qr_code");
    });

    test("fails if the external QR code payment interface fails", async () => {
        const { paymentPage, store, paymentExternalQrWithError } = await setupPaymentPage();
        paymentPage.state.paymentMethodId = paymentExternalQrWithError.id;

        await paymentPage.startPayment();

        expect(paymentExternalQrWithError.payment_interface.hasBeenCalled).toBe(true);
        expect(store.paymentError).toBe(true);
    });
});
