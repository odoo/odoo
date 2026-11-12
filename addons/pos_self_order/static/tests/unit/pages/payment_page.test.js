import { test, describe, expect, queryOne, click } from "@odoo/hoot";
import { mountWithCleanup, onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { PaymentPage } from "@pos_self_order/app/pages/payment_page/payment_page";
import { setupSelfPosEnv, getFilledSelfOrder } from "../utils";
import { definePosSelfModels } from "../data/generate_model_definitions";
import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";
import { advanceTime } from "@odoo/hoot-mock";

definePosSelfModels();

class MockPaymentInterface extends PaymentInterface {
    setup() {
        this.hasBeenCalled = false;
        this.hasBeenCancelled = false;
        this.amountPaid = 0;
        this.amountChange = 0;
    }
    startPayment() {
        this.hasBeenCalled = true;
        return { transaction_id: "mock_tx_id" };
    }
    cancelTransaction(transactionId) {
        this.cancelledTransaction = transactionId;
    }
}

class MockQrPaymentInterface extends MockPaymentInterface {
    startPayment() {
        return { ...super.startPayment(...arguments), qr_code: "mock_qr_code" };
    }
}

class MockPaymentInterfaceWithError extends MockPaymentInterface {
    startPayment() {
        this.hasBeenCalled = true;
        throw new Error("error");
    }
}

const mockBackendResponse = {
    order: [{}],
};

const setupPaymentPage = async () => {
    const store = await setupSelfPosEnv();

    const paymentNoProvider = store.models["pos.payment.method"].create({
        name: "Card",
        payment_provider: null,
    });

    const paymentTerminal = store.models["pos.payment.method"].create({
        name: "Terminal",
        payment_provider: "mock_terminal",
        payment_method_type: "terminal",
    });
    paymentTerminal.payment_interface = new MockPaymentInterface();

    const paymentTerminalWithError = store.models["pos.payment.method"].create({
        name: "TerminalError",
        payment_provider: "mock_terminal",
        payment_method_type: "terminal",
    });
    paymentTerminalWithError.payment_interface = new MockPaymentInterfaceWithError();

    const paymentQr = store.models["pos.payment.method"].create({
        name: "QR",
        payment_provider: "mock_qr",
        payment_method_type: "qr",
    });
    paymentQr.payment_interface = new MockQrPaymentInterface();

    const paymentQrWithError = store.models["pos.payment.method"].create({
        name: "QRError",
        payment_provider: "mock_qr",
        payment_method_type: "qr",
    });
    paymentQrWithError.payment_interface = new MockPaymentInterfaceWithError();

    const paymentCashMachine = store.models["pos.payment.method"].create({
        name: "CashMachine",
        payment_provider: "mock_cash_machine",
        payment_method_type: "cash_machine",
    });
    paymentCashMachine.payment_interface = new MockPaymentInterface();

    await getFilledSelfOrder(store);
    const paymentPage = await mountWithCleanup(PaymentPage, {});

    return {
        paymentPage,
        store,
        paymentNoProvider,
        paymentTerminal,
        paymentTerminalWithError,
        paymentQr,
        paymentQrWithError,
        paymentCashMachine,
    };
};

const clickPaymentMethod = async (paymentMethod) => {
    const paymentMethodButton = queryOne(`button:text(${paymentMethod.name})`);
    await click(paymentMethodButton);
};

const clickBackButton = async () => {
    const backButton = queryOne(`button:text(Back)`);
    await click(backButton);
};

describe("startPayment", () => {
    test("succeeds if the backend returns no error", async () => {
        const { store, paymentNoProvider } = await setupPaymentPage();

        onRpc("/kiosk/payment/1/kiosk", () => mockBackendResponse);
        await clickPaymentMethod(paymentNoProvider);

        expect(store.paymentError).toBe(false);
    });

    test("fails if the backend returns an error", async () => {
        const { store, paymentNoProvider } = await setupPaymentPage();

        onRpc("/kiosk/payment/1/kiosk", () => {
            throw new Error();
        });
        await clickPaymentMethod(paymentNoProvider);

        expect(store.paymentError).toBe(true);
    });

    test("succeeds if the payment terminal succeeds and backend returns no error", async () => {
        const { store, paymentTerminal } = await setupPaymentPage();

        onRpc("/kiosk/payment/1/kiosk", () => mockBackendResponse);
        await clickPaymentMethod(paymentTerminal);

        expect(paymentTerminal.payment_interface.hasBeenCalled).toBe(true);
        expect(store.paymentError).toBe(false);
    });

    test("fails if the payment terminal fails", async () => {
        const { store, paymentTerminalWithError } = await setupPaymentPage();
        await clickPaymentMethod(paymentTerminalWithError);

        onRpc("/kiosk/payment/1/kiosk", () => mockBackendResponse);
        await clickPaymentMethod(paymentTerminalWithError);

        expect(paymentTerminalWithError.payment_interface.hasBeenCalled).toBe(true);
        expect(store.paymentError).toBe(true);
    });

    test("does not call the payment terminal when the backend returns an error", async () => {
        const { store, paymentTerminal } = await setupPaymentPage();
        await clickPaymentMethod(paymentTerminal);

        onRpc("/kiosk/payment/1/kiosk", () => {
            throw new Error();
        });
        await clickPaymentMethod(paymentTerminal);

        expect(paymentTerminal.payment_interface.hasBeenCalled).toBe(false);
        expect(store.paymentError).toBe(true);
    });

    test("succeeds if the QR code payment interface succeeds and backend returns no error", async () => {
        const { paymentPage, store, paymentQr } = await setupPaymentPage();

        onRpc("/kiosk/payment/1/kiosk", () => mockBackendResponse);
        await clickPaymentMethod(paymentQr);

        expect(paymentQr.payment_interface.hasBeenCalled).toBe(true);
        expect(store.paymentError).toBe(false);
        await advanceTime(500); // Wait timeout fade out
        expect(paymentPage.state.qrCode).toBe("mock_qr_code");
    });

    test("fails if the QR code payment interface fails", async () => {
        const { store, paymentQrWithError } = await setupPaymentPage();

        onRpc("/kiosk/payment/1/kiosk", () => mockBackendResponse);
        await clickPaymentMethod(paymentQrWithError);

        expect(paymentQrWithError.payment_interface.hasBeenCalled).toBe(true);
        expect(store.paymentError).toBe(true);
    });

    test("succeeds if the cash machine payment interface succeeds", async () => {
        const { store, paymentCashMachine } = await setupPaymentPage();

        onRpc("/kiosk/payment/1/kiosk", () => mockBackendResponse);
        await clickPaymentMethod(paymentCashMachine);

        expect(paymentCashMachine.payment_interface.hasBeenCalled).toBe(true);
        expect(store.paymentError).toBe(false);
    });

    test("cancels cash machine payment when Back is pressed", async () => {
        const { store, paymentCashMachine } = await setupPaymentPage();

        patchWithCleanup(store.dialog, {
            add: (component, { confirm }) => confirm(true),
        });

        onRpc("/kiosk/payment/1/kiosk", () => mockBackendResponse);
        await clickPaymentMethod(paymentCashMachine);
        await clickBackButton();

        expect(paymentCashMachine.payment_interface.cancelledTransaction).toBe("mock_tx_id");
    });

    test("sends the signed partner of the order to the backend", async () => {
        const { store, paymentNoProvider } = await setupPaymentPage();
        const signedPartnerId = "7-0123456789abcdef";
        const connectedData = store.models.connectNewData({
            "res.partner": [{ id: signedPartnerId, name: "Demo User" }],
        });
        store.currentOrder.partner_id = connectedData["res.partner"][0];

        let sentOrder;
        onRpc("/kiosk/payment/1/kiosk", async (request) => {
            const { params } = await request.json();
            sentOrder = params.order;
            return mockBackendResponse;
        });
        await clickPaymentMethod(paymentNoProvider);

        expect(store.paymentError).toBe(false);
        expect(sentOrder.partner_id).toBe(signedPartnerId);
    });
});
