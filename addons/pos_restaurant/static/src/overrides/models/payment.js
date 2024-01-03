/** @odoo-module */

import { PaymentInterface } from "@point_of_sale/app/payment/payment_interface";
import { patch } from "@web/core/utils/patch";

patch(PaymentInterface.prototype, {
    /**
     * Return true if the amount that was authorized can be modified,
     * false otherwise
     * @param {string} uuid - The id of the paymentline
     */
    canBeAdjusted(uuid) {
        return false;
    },

    /**
     * Called when the amount authorized by a payment request should
     * be adjusted to account for a new order line, it can only be called if
     * canBeAdjusted returns True
     * @param {string} uuid - The id of the paymentline
     */
    send_payment_adjust(uuid) {},
});
