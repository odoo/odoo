import { expect, test } from "@odoo/hoot";
import { patch } from "@web/core/utils/patch";
import { PaymentBankTransfer } from "@point_of_sale/app/utils/payment/payment_bank_transfer";
import { createPaymentLine, getFilledOrder, setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";

definePosModels();

test("PaymentBankTransfer", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    const paymentline = createPaymentLine(store, order, card);
    const bankTransfer = new PaymentBankTransfer(store, card);

    expect(bankTransfer.supports_refunds).toBe(false);
    expect(bankTransfer.auto_send_request).toBe(true);

    // The request resolves with the cashier's answer in the QR popup
    let isConfirmed = true;
    patch(store, { showQR: async () => isConfirmed });
    expect(await bankTransfer.sendPaymentRequest(paymentline)).toBe(true);
    isConfirmed = false;
    expect(await bankTransfer.sendPaymentRequest(paymentline)).toBe(false);

    // Nothing to cancel on the bank side
    expect(await bankTransfer.sendPaymentCancel(paymentline)).toBe(true);
});
