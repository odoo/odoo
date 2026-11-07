/** @odoo-module */

export function clickCancel() {
    return [
        {
            content: "click cancel button",
            trigger: ".online-payment-popup .footer .cancel",
        },
    ];
}
export function fakeOnlinePaymentPaidData() {
    return [
        {
            content: "fake online payment paid data",
            trigger: ".online-payment-popup",
            run: () => {
                const currentOrder = odoo.__WOWL_DEBUG__.root.env.services.pos.get_order();

                const fakePaidOrder = currentOrder.export_as_JSON();
                fakePaidOrder.id = currentOrder.server_id;

                currentOrder.process_online_payments_data_from_server({
                    id: currentOrder.server_id,
                    paid_order: fakePaidOrder,
                });
            },
        },
    ];
}

export function isShown() {
    return [
        {
            content: "online payment popup is shown",
            trigger: ".modal-dialog .online-payment-popup",
            isCheck: true,
        },
    ];
}
export function isNotShown() {
    return [
        {
            content: "online payment popup is not shown",
            trigger: "body:not(:has(.online-payment-popup))",
            isCheck: true,
        },
    ];
}

/**
 * Check if the displayed amount to pay is the provided amount.
 * @param {String} amount
 */
export function amountIs(amount) {
    return [
        {
            content: `displayed amount is ${amount}`,
            trigger: `.online-payment-popup .body .info .amount:contains("${amount}")`,
            isCheck: true,
        },
    ];
}
