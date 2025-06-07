/** @odoo-module */

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

function generateLocalTicketNumber() {
    const today = new Date();
    const todayString = today.toDateString();
    const lastResetDate = localStorage.getItem("pos.last_reset_date");
    let currentCounter = parseInt(localStorage.getItem("pos.ticket_number")) || 0;

    let newTicketNumber;
    if (lastResetDate !== todayString) {
        newTicketNumber = 1;
        localStorage.setItem("pos.last_reset_date", todayString);
    } else {
        newTicketNumber = currentCounter + 1;
    }

    localStorage.setItem("pos.ticket_number", newTicketNumber.toString());
    return newTicketNumber;
}

async function getTicketNumber(orderId) {
    try {
        const response = await fetch('/custom_module/ticketNumber', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ order_id: orderId }),
        });
        if (response.ok) {
            const data = await response.json();
            return data.result.ticket_number;
        }
    } catch (error) {
        console.warn("Offline mode or server error", error);
    }
    return 0;
}
patch(PosOrder.prototype, {

    async setup(vals) {
        await super.setup(vals);

        try {
            const result = await getTicketNumber(parseInt(vals.id));

            if (result === 0) {
                const localTicketNumber = generateLocalTicketNumber();
                this.ticket_number = localTicketNumber;
                vals.ticket_number = localTicketNumber;
            } else {
                this.ticket_number = result;
                vals.ticket_number = result;
                localStorage.setItem("pos.ticket_number", result.toString());
            }
        } catch (error) {
            const fallbackNumber = generateLocalTicketNumber();
            this.ticket_number = fallbackNumber;
            vals.ticket_number = fallbackNumber;
            console.error("Error in setup ticket number, fallback to offline", error);
        }

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
            this.general_note = "";
        }
        return true;
    }





});