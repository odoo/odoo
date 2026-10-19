import { expect, test } from "@odoo/hoot";
import { queryOne, waitFor } from "@odoo/hoot-dom";
import { registry } from "@web/core/registry";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { setupCustomerDisplay } from "@point_of_sale/../tests/unit/customer_display/utils";

definePosModels();

const LIPA_NA_MPESA_ID = 8;

/** Adds a Lipa na M-PESA payment line, ready for its request to be sent. */
const addLipaNaMpesaPayment = (store, order) => {
    const paymentMethod = store.models["pos.payment.method"].get(LIPA_NA_MPESA_ID);
    const PaymentSafaricom = registry.category("pos_payment_providers").get("safaricom");
    paymentMethod.payment_interface = new PaymentSafaricom(store, paymentMethod);

    const { data: line } = order.addPaymentline(paymentMethod);
    // Lipa na M-PESA refuses anything but a rounded amount.
    line.setAmount(10);
    return line;
};

test("LipaNaMpesa: the customer display shows the QR code to scan", async () => {
    const [store, order] = await setupCustomerDisplay();
    await store.addLineToCurrentOrder({ product_tmpl_id: 5 });
    const line = addLipaNaMpesaPayment(store, order);

    // Not awaited: the request only settles once the cashier closes the
    // transaction popup, while the QR is meant to be on the display before that.
    line.payment_method_id.payment_interface.sendPaymentRequest(line);

    await waitFor(".qr-payment-card");
    // The QR reached the payment line, and the display renders one for it.
    expect(line.qr_code).toMatch(/^data:image\/png;base64,/);
    expect(queryOne(".qr-payment-card img.qr-image").src).toMatch(/^data:image\/png;base64,/);
    expect(".qr-payment-card .qr-amount").toHaveText("Amount: $ 10.00");
});
