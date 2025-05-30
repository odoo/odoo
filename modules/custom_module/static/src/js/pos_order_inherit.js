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
    },
      /**
     * A wrapper around line.delete() that may potentially remove multiple orderlines.
     * In core pos, it removes the linked combo lines. In other modules, it may remove
     * other related lines, e.g. multiple reward lines in pos_loyalty module.
     * @param {Orderline} line
     * @returns {boolean} true if the line was removed, false otherwise
     */
    removeOrderline(line) {
        console.log("removeOrderline22", line);
        const linesToRemove = line.getAllLinesInCombo();
        for (const lineToRemove of linesToRemove) {
            if (lineToRemove.refunded_orderline_id?.uuid in this.uiState.lineToRefund) {
                delete this.uiState.lineToRefund[lineToRemove.refunded_orderline_id.uuid];
            }

            if (this.assert_editable()) {
                lineToRemove.delete();
            }
        }
        if (!this.lines.length) {
            this.general_note = ""; // reset general note on empty order
        }
        return true;
    }





});