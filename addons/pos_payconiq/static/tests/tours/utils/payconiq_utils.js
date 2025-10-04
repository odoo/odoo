/* global posmodel */

export function wait(delay) {
    return {
        content: `wait for ${delay} ms`,
        trigger: "body",
        run: async () => await new Promise((resolve) => setTimeout(resolve, delay)),
    };
}

/* ----------------------------- PAYMENT ACTIONS ---------------------------- */
export function clickSendPayment() {
    return {
        content: "click send payment button",
        trigger: ".paymentline .send_payment_request",
        run: "click",
    };
}

export function clickCancelPayment() {
    return {
        content: "click cancel payment button",
        trigger: ".paymentline .external_qr_cancel",
        run: "click",
    };
}

export function clickConfirmPayment() {
    return {
        content: "click confirm payment button",
        trigger: ".paymentline .external_qr_confirm",
        run: "click",
    };
}

export function mockCallbackPayconic(status, fromEnd = 1) {
    return [
        wait(500),
        {
            content: "mock scan QR code",
            trigger: ".paymentline .external_qr_confirm",
            run: async () => {
                const orm = posmodel.env.services.orm;
                const response = await orm.searchRead("pos.payment.payconiq", [], ["payconiq_id"], {
                    limit: fromEnd,
                    order: "id desc",
                });
                if (!response || response.length < fromEnd) {
                    throw new Error("Not enough Payconiq payments found to mock scan QR code");
                }

                fetch("/webhook/payconiq", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({
                        paymentId: response[fromEnd - 1].payconiq_id,
                        status: status,
                    }),
                });
            },
        },
        wait(500),
    ].flat();
}

/* --------------------------- PAYMENT LINE STATUS -------------------------- */
export function isPaymentLinePending() {
    return {
        content: `check if payment line is pending`,
        trigger: `.paymentline .send_payment_request:contains('Send')`,
    };
}

export function isPaymentLineRetry() {
    return {
        content: `check if payment line is retry`,
        trigger: `.paymentline .send_payment_request:contains('Retry')`,
    };
}

export function isPaymentLineWaitingExternalQR() {
    return {
        content: `check if payment line is waiting for processing external QR`,
        trigger: `.paymentline .external_qr_confirm`,
    };
}

export function isPaymentLineDone() {
    return {
        content: `check if payment line is done`,
        trigger: `.paymentline .electronic_status:contains('Successful')`,
    };
}

/* --------------------------- SIMULTANEOUS ORDERS -------------------------- */
export function clickNewOrder() {
    return {
        content: "click new order button",
        trigger: ".pos-leftheader .list-plus-btn",
        run: "click",
    };
}

export function clickOrder(number) {
    return {
        content: `click order ${number}`,
        trigger: `.pos-leftheader .list-container-items .floating-order-container > button:contains('${number}')`,
        run: "click",
    };
}
