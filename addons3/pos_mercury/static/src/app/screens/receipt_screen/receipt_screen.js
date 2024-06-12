/** @odoo-module */

import { Order } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

patch(Order.prototype, {
    export_for_printing() {
        return {
            ...super.export_for_printing(),
            hasPosMercurySignature: this.get_paymentlines().some((line) => {
                line.mercury_data;
            }),
        };
    },
});
