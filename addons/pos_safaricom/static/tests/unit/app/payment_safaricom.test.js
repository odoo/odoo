import { expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import { animationFrame, click } from "@odoo/hoot-dom";
import {
    createPaymentLine,
    getFilledOrder,
    setupPosEnv,
    activateMountingDialogs,
} from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { registry } from "@web/core/registry";

definePosModels();

async function setupSafaricomEnv() {
    const store = await setupPosEnv();
    const pm7 = store.models["pos.payment.method"].get(7);
    const pm8 = store.models["pos.payment.method"].get(8);
    store.config.payment_method_ids = [...store.config.payment_method_ids, pm7, pm8];
    const PaymentInterface = registry.category("pos_payment_providers").get("safaricom", null);
    if (PaymentInterface) {
        pm7.payment_interface = new PaymentInterface(store, pm7);
        pm8.payment_interface = new PaymentInterface(store, pm8);
    }
    return store;
}

test("MpesaExpressTour: mpesa express asks phone number and sends request", async () => {
    const store = await setupSafaricomEnv();
    const order = await getFilledOrder(store);
    await activateMountingDialogs(store.env);
    const mpesaExpress = store.models["pos.payment.method"].get(7);
    const paymentline = createPaymentLine(store, order, mpesaExpress, { amount: 10 });

    const captured = {};
    const paymentInterface = paymentline.payment_interface;
    paymentInterface._call_safaricom = async (data, action) => {
        captured.action = action;
        captured.data = data;
        return {
            success: false,
            checkout_request_id: "CO_TEST_123",
            merchant_request_id: "TEST-MR-123",
        };
    };

    const paymentPromise = paymentInterface.sendPaymentRequest(paymentline);
    await animationFrame();

    await contains(".modal-dialog .form-control").edit("254712345678");
    await click(".modal-footer .btn-primary");
    await animationFrame();

    expect(captured.action).toBe("mpesa_express_send_payment_request");
    expect(captured.data.amount).toBe(10);
    expect(captured.data.phone_number).toBe("254712345678");
    expect(paymentline.payment_status).toBe("waitingCard");
    expect(paymentline.uiState.safaricom_checkout_request_id).toBe("CO_TEST_123");
    expect(paymentline.uiState.safaricom_merchant_request_id).toBe("TEST-MR-123");

    paymentInterface.completePayment(paymentline, true);
    expect(await paymentPromise).toBe(true);
});

test("LipaNaMpesaTour: lipa na mpesa shows qr popup and cancel sets retry", async () => {
    const store = await setupSafaricomEnv();
    const order = await getFilledOrder(store);
    await activateMountingDialogs(store.env);
    const lipaNaMpesa = store.models["pos.payment.method"].get(8);
    const paymentline = createPaymentLine(store, order, lipaNaMpesa, { amount: 15 });

    const paymentInterface = paymentline.payment_interface;
    paymentInterface._call_safaricom = async (data, action) => {
        if (action === "generate_qr_code") {
            return "iVBORw0KGgoAAAANSUhEUgAAAAEAAAAB";
        }
        return true;
    };

    const paymentPromise = paymentInterface.sendPaymentRequest(paymentline);
    await animationFrame();

    expect(".modal-dialog").toHaveCount(1);
    await click(".modal button.ms-auto");
    await animationFrame();
    expect(".modal-dialog img[alt='M-Pesa QR Code']").toHaveCount(1);
    await click(".modal button.btn-secondary:not(.ms-auto)");
    await animationFrame();

    expect(await paymentPromise).toBe(false);
    expect(paymentline.payment_status).toBe("retry");
});
