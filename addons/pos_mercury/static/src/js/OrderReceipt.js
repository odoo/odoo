/** @odoo-module */

import { OrderReceipt } from "@point_of_sale/js/Screens/ReceiptScreen/OrderReceipt";
import { patch } from "@web/core/utils/patch";

patch(OrderReceipt.prototype, "pos_mercury.OrderReceipt", {
    /**
     * The receipt has signature if one of the paymentlines
     * is paid with mercury.
     */
    get hasPosMercurySignature() {
        for (const line of this.paymentlines) {
            if (line.mercury_data) {
                return true;
            }
        }
        return false;
    },
});
