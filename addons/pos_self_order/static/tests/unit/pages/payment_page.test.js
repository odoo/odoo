import { test, describe, expect } from "@odoo/hoot";
import { mountWithCleanup, onRpc } from "@web/../tests/web_test_helpers";
import { PaymentPage } from "@pos_self_order/app/pages/payment_page/payment_page";
import { setupSelfPosEnv, getFilledSelfOrder } from "../utils";
import { definePosSelfModels } from "../data/generate_model_definitions";
import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";

definePosSelfModels();

class MockPaymentInterface extends PaymentInterface {
    setup() {
        this.hasBeenCalled = false;
    }
    sendPaymentRequest() {
        this.hasBeenCalled = true;
        return true;
    }
}

class MockPaymentInterfaceWithError extends MockPaymentInterface {
    sendPaymentRequest() {
        this.hasBeenCalled = true;
        return false;
    }
}

const setupPaymentPage = async () => {
    const store = await setupSelfPosEnv();

    const nonPaymentTerminal = store.models["pos.payment.method"].create({
        use_payment_terminal: null,
    });
    const paymentTerminal = store.models["pos.payment.method"].create({
        use_payment_terminal: "mock_terminal",
    });
    paymentTerminal.payment_terminal = new MockPaymentInterface();
    const paymentTerminalWithError = store.models["pos.payment.method"].create({
        use_payment_terminal: "mock_terminal",
    });
    paymentTerminalWithError.payment_terminal = new MockPaymentInterfaceWithError();
    await getFilledSelfOrder(store);

    const paymentPage = await mountWithCleanup(PaymentPage, {});

    return { paymentPage, store, nonPaymentTerminal, paymentTerminal, paymentTerminalWithError };
};

describe("startPayment", () => {
    test("succeeds if the backend returns no error", async () => {
        const { paymentPage, store, nonPaymentTerminal } = await setupPaymentPage();
        paymentPage.state.paymentMethodId = nonPaymentTerminal.id;

        onRpc("/kiosk/payment/1/kiosk", () => true);
        await paymentPage.startPayment();

        expect(store.paymentError).toBe(false);
    });

    test("fails if the backend returns an error", async () => {
        const { paymentPage, store, nonPaymentTerminal } = await setupPaymentPage();
        paymentPage.state.paymentMethodId = nonPaymentTerminal.id;

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

        expect(paymentTerminal.payment_terminal.hasBeenCalled).toBe(true);
        expect(store.paymentError).toBe(false);
    });

    test("fails if the payment terminal fails", async () => {
        const { paymentPage, store, paymentTerminalWithError } = await setupPaymentPage();
        paymentPage.state.paymentMethodId = paymentTerminalWithError.id;

        onRpc("/kiosk/payment/1/kiosk", () => true);
        await paymentPage.startPayment();

        expect(paymentTerminalWithError.payment_terminal.hasBeenCalled).toBe(true);
        expect(store.paymentError).toBe(true);
    });

    test("fails if the payment terminal succeeds but the backend returns an error", async () => {
        const { paymentPage, store, paymentTerminal } = await setupPaymentPage();
        paymentPage.state.paymentMethodId = paymentTerminal.id;

        onRpc("/kiosk/payment/1/kiosk", () => {
            throw new Error();
        });
        await paymentPage.startPayment();

        expect(paymentTerminal.payment_terminal.hasBeenCalled).toBe(true);
        expect(store.paymentError).toBe(true);
    });
});
