/** @odoo-module */

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";



patch(PosOrder.prototype, {

    setup(vals) {
        super.setup(vals);
        console.log("this Setup original");
        this.ticket_number = vals.ticket_number ;
        console.log("vals",vals);
    },

    /* This function is called after the order has been successfully sent to the preparation tool(s). */
    // @Override
    updateLastOrderChange() {

        const res = super.updateLastOrderChange();
    }
});