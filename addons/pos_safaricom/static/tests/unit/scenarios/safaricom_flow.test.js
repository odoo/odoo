import { expect, test } from "@odoo/hoot";
import { animationFrame, click, waitFor } from "@odoo/hoot-dom";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import { registry } from "@web/core/registry";
import { createTestProduct, setupAndMountPosApp } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import * as Utils from "@point_of_sale/../tests/unit/ui_utils";

definePosModels();

const MPESA_EXPRESS_ID = 7;
const LIPA_NA_MPESA_ID = 8;

async function setupSafaricomPos() {
    const store = await setupAndMountPosApp({ use_pricelist: false });
    const PaymentSafaricom = registry.category("pos_payment_providers").get("safaricom");

    for (const id of [MPESA_EXPRESS_ID, LIPA_NA_MPESA_ID]) {
        const paymentMethod = store.models["pos.payment.method"].get(id);
        paymentMethod.payment_interface = new PaymentSafaricom(store, paymentMethod);
        store.config.payment_method_ids = [...store.config.payment_method_ids, paymentMethod];
    }

    createTestProduct(store, { id: 9990, name: "Desk Pad", price: 10 });
    await animationFrame();
    return store;
}

async function payWith(paymentMethodName) {
    await Utils.clickDisplayedProduct("Desk Pad");
    await Utils.clickPayButton();
    await Utils.clickPaymentMethod(paymentMethodName);
    await click(".paymentline_status_actions_button_send");
    await animationFrame();
}

test("MpesaExpressTour: the phone number is asked and sent with the payment request", async () => {
    const store = await setupSafaricomPos();
    let requestData;
    onRpc("pos.payment.method", "mpesa_express_send_payment_request", ({ args }) => {
        requestData = args[1];
        return {
            success: false,
            checkout_request_id: "CO_TEST_123",
            merchant_request_id: "TEST-MR-123",
        };
    });

    await payWith("M-PESA Express");

    await contains(".modal textarea").edit("254712345678");
    await click(`.modal .modal-footer .btn-primary`);
    await animationFrame();

    const paymentLine = store.getOrder().payment_ids[0];
    expect(requestData.amount).toBe(10);
    expect(requestData.phone_number).toBe("254712345678");
    expect(paymentLine.payment_status).toBe("waitingCard");
    expect(paymentLine.uiState.safaricom_checkout_request_id).toBe("CO_TEST_123");
    expect(paymentLine.uiState.safaricom_merchant_request_id).toBe("TEST-MR-123");

    paymentLine.payment_interface.completePayment(paymentLine, true);
    await animationFrame();
    expect(paymentLine.payment_status).toBe("done");
});

test("LipaNaMpesaTour: the QR code can be displayed and cancelling the popup sets the line to retry", async () => {
    const store = await setupSafaricomPos();

    await payWith("Lipa na M-PESA");

    await waitFor(".modal");
    expect(`.modal img[alt="M-Pesa QR Code"]`).toHaveCount(0);
    await click(".modal .btn-secondary.ms-auto");
    await animationFrame();
    expect(`.modal img[alt="M-Pesa QR Code"]`).toHaveCount(1);

    await click(`.modal .btn-secondary:not(.ms-auto)`);
    await animationFrame();

    const paymentLine = store.getOrder().payment_ids[0];
    expect(paymentLine.payment_status).toBe("retry");
});

test("LipaNaMpesaTour: accepting a transaction validates the payment line", async () => {
    const store = await setupSafaricomPos();

    await payWith("Lipa na M-PESA");

    await waitFor(`.modal .table td:contains("A Test Customer")`);
    await click(`.modal .table .btn-primary`);
    await animationFrame();

    const paymentLine = store.getOrder().payment_ids[0];
    expect(paymentLine.payment_status).toBe("done");
    expect(paymentLine.amount).toBe(10);
    expect(paymentLine.cardholder_name).toBe("254712345678");
    expect(paymentLine.card_type).toBe("M-Pesa");
});
