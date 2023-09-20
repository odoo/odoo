/** @odoo-module */

import { Order } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

patch(Order.prototype, {
    getOrderReceiptEnv() {
        const receiptData = super.getOrderReceiptEnv();

        receiptData.hasPosMercurySignature = receiptData.paymentlines.some((line) => {
            if (line.mercury_data) {
                return true;
            }
        });

        return receiptData;
    },
});
