/** @odoo-module */

import { PosPayment } from "@point_of_sale/app/models/pos_payment";
import { patch } from "@web/core/utils/patch";

patch(PosPayment.prototype, {
    //@override
    canBeAdjusted() {
        if (this.payment_method_id.payment_terminal) {
            return this.payment_method_id.payment_terminal.canBeAdjusted(this.uuid);
        }
        return !this.payment_method_id.is_cash_count;
    },
});
