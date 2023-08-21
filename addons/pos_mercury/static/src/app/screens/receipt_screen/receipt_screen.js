/** @odoo-module */

import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { patch } from "@web/core/utils/patch";

patch(ReceiptScreen.prototype, {
    get receiptData() {
        const receiptData = super.receiptData;

        receiptData.hasPosMercurySignature = receiptData.paymentlines.some((line) => {
            if (line.mercury_data) {
                return true;
            }
        });

        return receiptData;
    },
});
