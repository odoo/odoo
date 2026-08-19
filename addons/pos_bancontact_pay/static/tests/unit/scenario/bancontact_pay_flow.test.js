import { expect, test } from "@odoo/hoot";
import { waitFor, waitUntil } from "@odoo/hoot-dom";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import * as PosUiUtils from "@point_of_sale/../tests/unit/ui_utils";
import * as BancontactUiUtils from "@pos_bancontact_pay/../tests/unit/ui_utils";

const Utils = { ...PosUiUtils, ...BancontactUiUtils };

const STICKER_BUSY = "This sticker is already processing another payment.";

definePosModels();

test("bancontact_pay_failed_to_create_payment: the payment request is refused with a 401", async () => {
    expect.errors(2);

    const store = await Utils.setupBancontactPos({ postStatusCode: 401 });
    await Utils.initOrder();
    const order = store.getOrder();

    await Utils.clickPaymentMethod(Utils.DISPLAY);
    await Utils.clickSendButton();
    expect(await Utils.dialogBody()).toInclude("(ERR: 401)");

    await Utils.confirmDialog();
    expect(Utils.actionState()).toBe("retry");

    await Utils.clickRetryButton();
    expect(await Utils.dialogBody()).toInclude("(ERR: 401)");

    await Utils.confirmDialog();
    expect(order.payment_ids).toHaveLength(1);
    expect(order.payment_ids[0].bancontact_id).toBeEmpty();

    await Utils.deletePaymentline({ name: Utils.DISPLAY, amount: "10.00" });
    expect(order.payment_ids).toHaveLength(0);
    expect.verifyErrors([/ERR: 401/, /ERR: 401/]);
});

test.tags("desktop");
test("bancontact_pay_can_send_request: a sticker handles a single payment at a time", async () => {
    const store = await Utils.setupBancontactPos();
    await Utils.initOrder();
    const order1 = store.getOrder();

    // Two display payments can run side by side. [A] and [B]
    await Utils.clickPaymentMethod(Utils.DISPLAY);
    await Utils.clickSendButton();
    await Utils.closeQrPopup();
    expect(Utils.actionState()).toBe("waiting_scan");

    await Utils.clickPaymentMethod(Utils.DISPLAY);
    await Utils.clickSendButton();
    await Utils.closeQrPopup();
    expect(Utils.actionState()).toBe("waiting_scan");

    // [C] takes the sticker.
    await Utils.clickPaymentMethod(Utils.STICKER_1);
    await Utils.clickSendButton();
    expect(Utils.actionState()).toBe("waiting_scan");

    // The sticker is busy, so no payment line is created at all.
    await Utils.clickPaymentMethod(Utils.STICKER_1);
    expect(await Utils.dialogBody()).toInclude(STICKER_BUSY);
    await Utils.confirmDialog();
    expect(Utils.countPaymentlines()).toBe(3);

    // Cancelling [C] frees the sticker for [D].
    await Utils.clickPaymentline({ name: Utils.STICKER_1, nth: 3 });
    await Utils.clickCancelButton();
    expect(Utils.actionState()).toBe("retry");

    await Utils.clickPaymentMethod(Utils.STICKER_1);
    await Utils.clickSendButton();
    expect(Utils.actionState()).toBe("waiting_scan");

    // Retrying [C] now conflicts with [D].
    await Utils.clickPaymentline({ name: Utils.STICKER_1, nth: 3 });
    await Utils.clickRetryButton();
    expect(await Utils.dialogBody()).toInclude(STICKER_BUSY);
    await Utils.confirmDialog();
    expect(Utils.actionState()).toBe("retry");

    // [E] takes the second sticker.
    await Utils.clickPaymentMethod(Utils.STICKER_2);
    await Utils.clickSendButton();
    expect(Utils.actionState()).toBe("waiting_scan");

    // [F] on a second order, the display is never blocked.
    await Utils.createFloatingOrder();
    await Utils.initOrder();
    const order2 = store.getOrder();
    await Utils.clickPaymentMethod(Utils.DISPLAY);
    await Utils.clickSendButton();
    await Utils.closeQrPopup();
    expect(Utils.actionState()).toBe("waiting_scan");

    // A sticker busy on another order is refused as well.
    await Utils.clickPaymentMethod(Utils.STICKER_2);
    expect(await Utils.dialogBody()).toInclude(STICKER_BUSY);
    await Utils.confirmDialog();
    expect(Utils.countPaymentlines()).toBe(1);

    // Cancelling [E] on the first order frees the sticker for the second one.
    await Utils.clickFloatingOrder(order1.getName());
    await Utils.clickPaymentline({ name: Utils.STICKER_2, nth: 5 });
    await Utils.clickCancelButton();
    expect(Utils.actionState()).toBe("retry");

    await Utils.clickFloatingOrder(order2.getName());
    await Utils.clickPaymentMethod(Utils.STICKER_2);
    await Utils.clickSendButton();
    expect(Utils.actionState()).toBe("waiting_scan");

    // Retrying [E] is now refused because of the second order.
    await Utils.clickFloatingOrder(order1.getName());
    await Utils.clickPaymentline({ name: Utils.STICKER_2, nth: 5 });
    await Utils.clickRetryButton();
    expect(await Utils.dialogBody()).toInclude(STICKER_BUSY);
    await Utils.confirmDialog();
    expect(Utils.actionState()).toBe("retry");
});

test("bancontact_pay_show_qr_code: the QR code popup follows its own payment line", async () => {
    const store = await Utils.setupBancontactPos({
        prefix: "bancontact_show_qr_code_",
    });
    await Utils.initOrder();

    // A display payment opens the popup by itself. (bancontact_show_qr_code_0)
    await Utils.clickPaymentMethod(Utils.DISPLAY);
    await Utils.clickSendButton();
    expect(Utils.selectedPaymentline()).toEqual({
        name: Utils.DISPLAY,
        amount: "$10.00",
    });
    expect(await Utils.qrPopupAmount()).toBe("$ 10.00");

    await Utils.closeQrPopup();
    await Utils.showQrPopup({ selected: true });
    expect(await Utils.qrPopupAmount()).toBe("$ 10.00");
    await Utils.closeQrPopup();

    // Cancelling drops the QR code.
    await Utils.clickCancelButton();
    expect(Utils.isShowQrPopupDisabled({ selected: true })).toBe(true);

    // Retrying asks for a new QR code, for the new amount. (…_1)
    await Utils.sendBufferKeys("2");
    expect(Utils.selectedPaymentline().amount).toBe("$2.00");
    await Utils.clickRetryButton();
    expect(await Utils.qrPopupAmount()).toBe("$ 2.00");

    await Utils.closeQrPopup();
    await Utils.showQrPopup({ selected: true });
    expect(await Utils.qrPopupAmount()).toBe("$ 2.00");
    await Utils.closeQrPopup();

    // A sticker payment never opens the popup on its own. (…_2)
    await Utils.clickPaymentMethod(Utils.STICKER_1);
    await Utils.clickSendButton();
    expect(Utils.selectedPaymentline()).toEqual({
        name: Utils.STICKER_1,
        amount: "$10.00",
    });
    expect(Utils.isQrPopupShown()).toBe(false);

    await Utils.showQrPopup({ selected: true });
    expect(await Utils.qrPopupAmount()).toBe("$ 10.00");
    await Utils.closeQrPopup();

    await Utils.clickCancelButton();
    expect(Utils.isShowQrPopupDisabled({ selected: true })).toBe(true);

    // (…_3)
    await Utils.sendBufferKeys("3");
    expect(Utils.selectedPaymentline().amount).toBe("$3.00");
    await Utils.clickRetryButton();
    expect(Utils.isQrPopupShown()).toBe(false);

    await Utils.showQrPopup({ selected: true });
    expect(await Utils.qrPopupAmount()).toBe("$ 3.00");
    await Utils.closeQrPopup();

    // The popup of an unselected line survives another line being paid.
    await Utils.showQrPopup({ name: Utils.DISPLAY });
    expect(await Utils.qrPopupAmount()).toBe("$ 2.00");
    await Utils.mockCallbackBancontactPay(store, "bancontact_show_qr_code_3", "SUCCEEDED");
    expect(await Utils.qrPopupAmount()).toBe("$ 2.00");

    // It closes as soon as its own line is paid.
    await Utils.mockCallbackBancontactPay(store, "bancontact_show_qr_code_1", "SUCCEEDED");
    expect(Utils.isQrPopupShown()).toBe(false);
    await Utils.closeNotifications();

    // A failed payment closes the popup too. (…_4)
    await Utils.clickPaymentMethod(Utils.DISPLAY);
    await Utils.clickSendButton();
    expect(Utils.selectedPaymentline()).toEqual({
        name: Utils.DISPLAY,
        amount: "$5.00",
    });
    expect(await Utils.qrPopupAmount()).toBe("$ 5.00");

    await Utils.mockCallbackBancontactPay(store, "bancontact_show_qr_code_4", "FAILED");
    expect(Utils.isQrPopupShown()).toBe(false);
});

test("bancontact_pay_success_payment: paid orders are notified and validated", async () => {
    const store = await Utils.setupBancontactPos({
        prefix: "bancontact_success_",
    });
    await Utils.initOrder();
    const order1 = store.getOrder();

    // [A] 5.00 and [B] 2.00 on the first order. (bancontact_success_1 and _3)
    for (const amount of ["5", "2"]) {
        await Utils.clickPaymentMethod(Utils.DISPLAY);
        await Utils.clickSendButton();
        expect(Utils.selectedPaymentline().amount).toBe("$10.00");
        await Utils.closeQrPopup();

        await Utils.clickCancelButton();
        expect(Utils.actionState()).toBe("retry");

        await Utils.sendBufferKeys(amount);
        expect(Utils.selectedPaymentline().amount).toBe(`$${amount}.00`);

        await Utils.clickRetryButton();
        await Utils.closeQrPopup();
        expect(Utils.actionState()).toBe("waiting_scan");
    }

    // [A] is paid while [B] is the selected line.
    await Utils.mockCallbackBancontactPay(store, "bancontact_success_1", "SUCCEEDED");
    const [received] = Utils.notifications();
    expect(received.type).toBe("success");
    expect(received.message).toBe("Payment received");
    await Utils.closeNotifications();

    await Utils.clickPaymentline({ name: Utils.DISPLAY, amount: "5.00" });
    expect(Utils.actionState()).toBe("paid");
    await Utils.clickPaymentline({ name: Utils.DISPLAY, amount: "2.00" });
    expect(Utils.actionState()).toBe("waiting_scan");

    // [B] is paid while selected: no notification.
    await Utils.mockCallbackBancontactPay(store, "bancontact_success_3", "SUCCEEDED");
    expect(Utils.actionState()).toBe("paid");
    expect(Utils.notifications()).toHaveLength(0);

    // [C] settles the order, which is validated automatically. (…_4)
    await Utils.clickPaymentMethod(Utils.DISPLAY);
    await Utils.clickSendButton();
    expect(Utils.selectedPaymentline().amount).toBe("$3.00");
    expect(Utils.actionState()).toBe("waiting_scan");

    await Utils.mockCallbackBancontactPay(store, "bancontact_success_4", "SUCCEEDED");
    await waitFor(".feedback-screen");
    await waitUntil(() => order1.state === "paid");
    expect(order1.state).toBe("paid");
    await Utils.clickNextOrder();

    // [D] 5.00 on a second order. (…_6)
    await Utils.initOrder();
    const order2 = store.getOrder();
    await Utils.clickPaymentMethod(Utils.DISPLAY);
    await Utils.clickSendButton();
    await Utils.closeQrPopup();
    await Utils.clickCancelButton();
    await Utils.sendBufferKeys("5");
    await Utils.clickRetryButton();
    await Utils.closeQrPopup();
    expect(Utils.actionState()).toBe("waiting_scan");

    // [D] is paid while a third order is on screen.
    await Utils.createFloatingOrder();
    const order3 = store.getOrder();
    await Utils.mockCallbackBancontactPay(store, "bancontact_success_6", "SUCCEEDED");
    const [partiallyPaid] = Utils.notifications();
    expect(partiallyPaid.type).toBe("success");
    expect(partiallyPaid.message).toInclude(
        `The order ${order2.floatingOrderName} has been partially paid.`
    );
    await Utils.closeNotifications();

    // [E] settles the second order from another order: no auto validation. (…_7)
    await Utils.clickFloatingOrder(order2.getName());
    await Utils.clickPaymentMethod(Utils.DISPLAY);
    await Utils.clickSendButton();
    expect(Utils.selectedPaymentline().amount).toBe("$5.00");
    await Utils.closeQrPopup();
    expect(Utils.actionState()).toBe("waiting_scan");

    await Utils.clickFloatingOrder(order3.getName());
    await Utils.mockCallbackBancontactPay(store, "bancontact_success_7", "SUCCEEDED");
    const [fullyPaid] = Utils.notifications();
    expect(fullyPaid.type).toBe("success");
    expect(fullyPaid.message).toInclude(
        `The order ${order2.floatingOrderName} has been fully paid.`
    );
    await Utils.closeNotifications();
    expect(order2.state).toBe("draft");

    await Utils.clickFloatingOrder(order2.getName());
    await Utils.clickValidatePayment();
    await waitFor(".feedback-screen");
    await waitUntil(() => order2.state === "paid");
    expect(order2.state).toBe("paid");

    // Forcing a payment done validates the order as well. (…_8)
    await Utils.clickNextOrder();
    await Utils.initOrder();
    const order4 = store.getOrder();
    await Utils.clickPaymentMethod(Utils.DISPLAY);
    await Utils.clickSendButton();
    await Utils.closeQrPopup();
    expect(Utils.actionState()).toBe("waiting_scan");

    await Utils.clickForceDoneButton();
    await waitFor(".feedback-screen");
    await waitUntil(() => order4.state === "paid");
    expect(order4.state).toBe("paid");
});

test("bancontact_pay_failed_payment: every failure status is reported to the cashier", async () => {
    const store = await Utils.setupBancontactPos({
        prefix: "bancontact_failed_",
    });
    await Utils.initOrder();
    const order = store.getOrder();

    const failures = [
        ["AUTHORIZATION_FAILED", "Payment failed"],
        ["FAILED", "Payment failed"],
        ["EXPIRED", "Payment expired"],
        ["CANCELLED", "Payment cancelled"],
    ];
    for (const [index, [status, message]] of failures.entries()) {
        await Utils.clickPaymentMethod(Utils.DISPLAY);
        await Utils.clickSendButton();
        expect(Utils.actionState()).toBe("waiting_scan");

        await Utils.mockCallbackBancontactPay(store, `bancontact_failed_${index}`, status);
        expect(Utils.actionState()).toBe("retry");
        expect(Utils.isQrPopupShown()).toBe(false);

        const [notification] = Utils.notifications();
        expect(notification.type).toBe("warning");
        expect(notification.message).toBe(message);
        await Utils.closeNotifications();
    }

    // A failure on another order is reported with the order name.
    await Utils.clickPaymentMethod(Utils.DISPLAY);
    await Utils.clickSendButton();
    await Utils.closeQrPopup();
    await Utils.createFloatingOrder();

    await Utils.mockCallbackBancontactPay(store, "bancontact_failed_4", "FAILED");
    const [notification] = Utils.notifications();
    expect(notification.type).toBe("warning");
    expect(notification.message).toBe(`A payment for order ${order.floatingOrderName} has failed.`);
});

test("bancontact_pay_failed_to_cancel_payment_error_422: the cancellation can be forced", async () => {
    const store = await Utils.setupBancontactPos({ deleteStatusCode: 422 });
    await Utils.initOrder();
    const order = store.getOrder();

    await Utils.clickPaymentMethod(Utils.DISPLAY);
    await Utils.clickSendButton();
    await Utils.closeQrPopup();
    expect(Utils.actionState()).toBe("waiting_scan");

    // Closing the dialog keeps the payment as is.
    await Utils.clickCancelButton();
    expect(await Utils.dialogBody()).toInclude("The customer is currently completing the payment");
    await Utils.confirmDialog();
    expect(Utils.actionState()).toBe("waiting_scan");
    expect(order.payment_ids[0].bancontact_id).toBe("bancontact_0");

    // Forcing the cancellation drops the payment locally.
    await Utils.clickCancelButton();
    expect(await Utils.dialogBody()).toInclude("The customer is currently completing the payment");
    // 'Force Cancel' is the dialog's cancel button.
    await Utils.cancelDialog();
    expect(Utils.actionState()).toBe("retry");
    expect(order.payment_ids[0].bancontact_id).toBeEmpty();

    // The payment request can be sent again.
    await Utils.clickRetryButton();
    await Utils.closeQrPopup();
    expect(Utils.actionState()).toBe("waiting_scan");
    expect(order.payment_ids[0].bancontact_id).toBe("bancontact_1");
});

test("bancontact_pay_failed_to_cancel_payment_error_429: other errors cancel silently", async () => {
    const store = await Utils.setupBancontactPos({ deleteStatusCode: 429 });
    await Utils.initOrder();
    const order = store.getOrder();

    await Utils.clickPaymentMethod(Utils.DISPLAY);
    await Utils.clickSendButton();
    await Utils.closeQrPopup();
    expect(Utils.actionState()).toBe("waiting_scan");

    // The error is swallowed and the payment is cancelled locally.
    await Utils.clickCancelButton();
    expect(Utils.actionState()).toBe("retry");
    expect(order.payment_ids[0].bancontact_id).toBeEmpty();

    await Utils.clickRetryButton();
    await Utils.closeQrPopup();
    expect(Utils.actionState()).toBe("waiting_scan");
    expect(order.payment_ids[0].bancontact_id).toBe("bancontact_1");
});
