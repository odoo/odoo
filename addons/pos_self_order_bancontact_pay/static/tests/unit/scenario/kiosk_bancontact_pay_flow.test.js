import { expect, test } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
import { definePosSelfModels } from "@pos_self_order/../tests/unit/data/generate_model_definitions";
import * as PosUiUtils from "@point_of_sale/../tests/unit/ui_utils";
import * as KioskUiUtils from "@pos_self_order_bancontact_pay/../tests/unit/ui_utils";

const Utils = { ...PosUiUtils, ...KioskUiUtils };

definePosSelfModels();

test("kiosk_bancontact_pay_success: scanning the QR code pays the kiosk order", async () => {
    const store = await Utils.setupKioskPaymentPage({ prefix: "kiosk_bancontact_success_" });

    await Utils.clickBancontactMethod();
    await Utils.isProcessingPayment();
    await Utils.waitForQrCode();

    const payment = Utils.lastPaymentline(store);
    expect(payment.payment_method_id.name).toBe(Utils.DISPLAY);
    expect(payment.bancontact_id).toBe("kiosk_bancontact_success_0");
    expect(payment.payment_status).toBe("waitingScan");
    expect.verifySteps([]);

    await Utils.mockCallbackBancontactPay(store, "kiosk_bancontact_success_0", "SUCCEEDED");

    expect(payment.payment_status).toBe("done");
    expect(store.paymentError).toBe(false);
    expect(Utils.notifications()).toHaveLength(0);
    expect.verifySteps(["kiosk payment"]);
});

test("kiosk_bancontact_pay_failed: a failed payment can be retried", async () => {
    const store = await Utils.setupKioskPaymentPage({ prefix: "kiosk_bancontact_failed_" });

    await Utils.clickBancontactMethod();
    await Utils.isProcessingPayment();
    await Utils.waitForQrCode();
    expect(Utils.lastPaymentline(store).bancontact_id).toBe("kiosk_bancontact_failed_0");

    await Utils.mockCallbackBancontactPay(store, "kiosk_bancontact_failed_0", "FAILED");

    expect(store.currentOrder.payment_ids).toHaveLength(0);
    expect(store.paymentError).toBe(true);
    const [failure] = Utils.notifications();
    expect(failure.type).toBe("danger");
    expect(failure.message).toInclude("Payment failed");
    await Utils.closeNotifications();
    expect.verifySteps([]);

    await Utils.clickBtn("Retry");
    await Utils.waitForQrCode();

    const payment = Utils.lastPaymentline(store);
    expect(payment.bancontact_id).toBe("kiosk_bancontact_failed_1");
    expect(payment.payment_status).toBe("waitingScan");
    expect(store.paymentError).toBe(false);

    await Utils.mockCallbackBancontactPay(store, "kiosk_bancontact_failed_1", "SUCCEEDED");

    expect(payment.payment_status).toBe("done");
    expect.verifySteps(["kiosk payment"]);
});

test("kiosk_bancontact_pay_failed_create_payment: the payment cannot be created", async () => {
    const store = await Utils.setupKioskPaymentPage({ postStatusCode: 401 });

    await Utils.clickBancontactMethod();
    await Utils.isProcessingPayment();

    await waitFor(".modal");
    expect(Utils.dialogTitle()).toBe("Bancontact Payment Error");
    expect(await Utils.dialogBody()).toInclude("(ERR: 401)");
    await Utils.confirmDialog();

    const [error] = Utils.notifications();
    expect(error.type).toBe("danger");
    expect(error.message).toBe("An error has occurred");
    await Utils.closeNotifications();

    expect(store.currentOrder.payment_ids).toHaveLength(0);
    expect(Utils.isQrCodeShown()).toBe(false);
    expect(store.paymentError).toBe(true);

    await Utils.clickBtn("Retry");
    await waitFor(".modal");
    expect(await Utils.dialogBody()).toInclude("(ERR: 401)");
    await Utils.confirmDialog();

    expect(Utils.notifications()[0].message).toBe("An error has occurred");
    expect(store.currentOrder.payment_ids).toHaveLength(0);
    expect.verifySteps([]);
});
