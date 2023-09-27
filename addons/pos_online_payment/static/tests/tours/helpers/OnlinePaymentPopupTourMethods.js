/** @odoo-module */

import * as Dialog from "@point_of_sale/../tests/tours/helpers/DialogTourMethods";

export function amountIs(amount) {
    return {
        content: `displayed amount is ${amount}`,
        trigger: `.amount:contains("${amount}")`,
        isCheck: true,
        is_modal: true,
    };
}

/**
 * Used to replace the POS bus web socket communication that doesn't seem to work when executing a test tour.
 * The server is regularly checked to see if the fake online payment has been done.
 *
 * @param {integer} checksAmount
 * @param {integer} delayBetweenChecks
 * @returns
 */
export function waitForOnlinePayment(checksAmount = 10, delayBetweenChecks = 3000) {
    return [
        {
            ...Dialog.is(),
            run: () => {
                let checkIndex = 0;
                const checkFunc = async () => {
                    const currentOrder = odoo.__WOWL_DEBUG__.root.env.services.pos.get_order();
                    let opData;
                    if (currentOrder) {
                        opData = await currentOrder.update_online_payments_data_with_server(
                            odoo.__WOWL_DEBUG__.root.env.services.orm,
                            false
                        );
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
        {
            ...Dialog.isNot(),
            timeout: checksAmount * delayBetweenChecks + 3000,
        },
    ];
}
