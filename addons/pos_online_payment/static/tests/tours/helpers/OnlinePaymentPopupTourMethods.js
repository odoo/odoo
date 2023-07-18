/** @odoo-module */

import { createTourMethods } from "@point_of_sale/../tests/tours/helpers/utils";

class Do {
    clickCancel() {
        return [
            {
                content: "click cancel button",
                trigger: ".online-payment-popup .footer .cancel",
            },
        ];
    }

    fakeOnlinePaymentPaidData() {
        return [
            {
                content: "fake online payment paid data",
                trigger: ".online-payment-popup",
                run: () => {
                    const currentOrder = odoo.__WOWL_DEBUG__.root.env.services.pos.get_order();

                    const fakePaidOrder = currentOrder.export_as_JSON();
                    fakePaidOrder.id = currentOrder.server_id;

                    currentOrder.process_online_payments_data_from_server({
                        "id": currentOrder.server_id,
                        "paid_order": fakePaidOrder,
                    });
                },
            },
        ];
    }
}

class Check {
    isShown() {
        return [
            {
                content: "online payment popup is shown",
                trigger: ".modal-dialog .online-payment-popup",
                isCheck: true,
            },
        ];
    }

    isNotShown() {
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
    amountIs(amount) {
        return [
            {
                content: `displayed amount is ${amount}`,
                trigger: `.online-payment-popup .body .info .amount:contains("${amount}")`,
                isCheck: true,
            },
        ];
    }

    /**
     * Used to replace the POS bus web socket communication that doesn't seem to work when executing a test tour.
     * The server is regularly checked to see if the fake online payment has been done.
     *
     * @param {integer} checksAmount
     * @param {integer} delayBetweenChecks
     * @returns
     */
    waitForOnlinePayment(checksAmount = 10, delayBetweenChecks = 3000) {
        const waitingStep = this.isNotShown()[0];
        waitingStep.content = "wait for online payment";
        waitingStep.timeout = checksAmount * delayBetweenChecks + 3000;
        return [
            {
                content: "start checks for online payment",
                trigger: ".online-payment-popup",
                run: () => {
                    let checkIndex = 0;
                    const checkFunc = async () => {
                        const currentOrder = odoo.__WOWL_DEBUG__.root.env.services.pos.get_order();
                        let opData;
                        if (currentOrder) {
                            opData = await currentOrder.update_online_payments_data_with_server(odoo.__WOWL_DEBUG__.root.env.services.orm, false);
                        }
                        const isMaxChecksReached = checkIndex >= checksAmount - 1;
                        const isOrderPaid = opData && opData.is_paid;
                        if (!isOrderPaid && !isMaxChecksReached) {
                            checkIndex++;
                            setTimeout(checkFunc, delayBetweenChecks);
                        }
                    };
                    setTimeout(checkFunc, delayBetweenChecks);
                },
            },
            waitingStep,
        ];
    }
}

// FIXME: this is a horrible hack to export an object as named exports.
// eslint-disable-next-line no-undef
Object.assign(__exports, createTourMethods("OnlinePaymentPopup", Do, Check));
