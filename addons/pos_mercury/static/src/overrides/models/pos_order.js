/** @odoo-module */

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    export_for_printing() {
        return {
            ...super.export_for_printing(),
            hasPosMercurySignature: this.payment_ids.some((line) => {
                line.mercury_data;
            }),
        };
    },
    electronic_payment_in_progress() {
        const res = super.electronic_payment_in_progress(...arguments);
        return res || this.payment_ids.some((line) => line.mercury_swipe_pending);
    },
});
