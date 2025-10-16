/* global posmodel */

import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";

// -------------------------------
// Bancontact Pay dialogs
// -------------------------------
export function apiErrorDialog(statusCode, close = true) {
    const steps = [];

    steps.push({
        content:
            "check that an error dialog due to the creation of the Bancontact Pay payment is displayed",
        trigger: `.o_alert_dialog .modal-body:contains("(ERR: ${statusCode})")`,
    });

    if (close) {
        steps.push(Dialog.confirm());
    }

    return steps.flat();
}

export function askForceCancelDialog(action) {
    const steps = [];

    steps.push({
        content: "check that the confirmation dialog to force cancel is displayed",
        trigger: `.o_confirmation_dialog .modal-body:contains("The customer is currently completing the payment")`,
    });

    if (action === "close") {
        steps.push(Dialog.confirm("Close"));
    } else if (action === "force_cancel") {
        steps.push(Dialog.confirm("Force Cancel", ".btn-secondary"));
    }

    return steps.flat();
}

export function stickerAlreadyProcessingDialog(close = true) {
    const steps = [];

    steps.push({
        content: "check that an error dialog due to the sticker already in use is displayed",
        trigger: `.o_alert_dialog .modal-body:contains("This sticker is already processing another payment.")`,
    });

    if (close) {
        steps.push(Dialog.confirm());
    }

    return steps.flat();
}

// -------------------------------
// Notifications
// -------------------------------
export function notifiedOrderPartiallyPaid(orderName) {
    return {
        content: `check that a notification for partially paid order ${orderName} is displayed`,
        trigger: `.o_notification:has(.o_notification_bar.bg-success):has(.o_notification_content:contains('The order ${orderName} has been partially paid.')) .o_notification_close`,
        run: "click",
    };
}

export function notifiedOrderFullyPaid(orderName) {
    return {
        content: `check that a notification for fully paid order ${orderName} is displayed`,
        trigger: `.o_notification:has(.o_notification_bar.bg-success):has(.o_notification_content:contains('The order ${orderName} has been fully paid.')) .o_notification_close`,
        run: "click",
    };
}

export function notifiedPaymentReceived() {
    return {
        content: "check that a notification for received payment is displayed",
        trigger: `.o_notification:has(.o_notification_bar.bg-success):has(.o_notification_content:contains('Payment received')) .o_notification_close`,
        run: "click",
    };
}

export function notifiedPaymentError(message) {
    return {
        content: "close the notification",
        trigger: `.o_notification:has(.o_notification_bar.bg-warning):has(.o_notification_content:contains('${message}')) .o_notification_close`,
        run: "click",
    };
}

// -------------------------------
// Bancontact payment callbacks
// -------------------------------
export function mockCallbackBancontactPay(status, fromEnd = 1) {
    const delay = 200; // ms
    return [
        {
            content: `wait for ${delay} ms`,
            trigger: "body",
            run: async () => {
                await new Promise((resolve) => setTimeout(resolve, delay));
            },
        },
        {
            content: "mock scan QR code",
            trigger: "body",
            run: async () => {
                const orm = posmodel.env.services.orm;
                const response = await orm.searchRead("pos.payment", [], ["bancontact_id"], {
                    limit: fromEnd,
                    order: "id desc",
                });
                if (!response || response.length < fromEnd) {
                    throw new Error("Not enough Bancontact payments found to mock scan QR code");
                }

                fetch("/bancontact_pay/webhook?mode=test", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({
                        paymentId: response[fromEnd - 1].bancontact_id,
                        status: status,
                    }),
                });
            },
        },
        {
            content: `wait for ${delay} ms`,
            trigger: "body",
            run: async () => {
                await new Promise((resolve) => setTimeout(resolve, delay));
            },
        },
    ].flat();
}

// -------------------------------
// Console error mocking
// -------------------------------
/**
 * Temporarily disables `console.error` during a test run.
 *
 * This helper is used when mocking failed Bancontact API responses.
 * In that scenario, the error is intentionally thrown and bubbles up,
 * which would normally trigger `console.error`.
 *
 * In the test environment, logging an error causes the backend to record
 * the error and marks the tour as failed, even though the failure is expected
 * and the test itself is successful.
 *
 * This setup step silences `console.error` to prevent false-negative test
 * failures caused by expected Bancontact HTTP errors.
 *
 * @param {Object} memo
 *   Mutable object used to store the original `console.error` reference
 *   so it can be restored during teardown.
 */
export function setupBancontactErrorHttp(memo) {
    return {
        content: "setup Bancontact error http mocking",
        trigger: "body",
        run: () => {
            memo.consoleError = console.error;
            console.error = () => {};
        },
    };
}

/**
 * Restores the original `console.error` after Bancontact HTTP error mocking.
 *
 * This teardown step re-enables normal error logging once the test is done,
 * ensuring that real errors are logged correctly outside of the mocked
 * Bancontact failure scenario.
 *
 * @param {Object} memo
 *   Mutable object used to store the original `console.error` reference.
 */
export function teardownBancontactErrorHttp(memo) {
    return {
        content: "teardown Bancontact error http mocking",
        trigger: "body",
        run: () => {
            console.error = memo.consoleError;
            memo.consoleError = null;
        },
    };
}
