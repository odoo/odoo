/** @odoo-module */

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

function checkForChanges() {
    let hasOtherChanges = false;
    const orderLines = document.querySelectorAll('.order-container .orderline');
    for (const line of orderLines) {
        if (line.classList.contains('has-change')) {
            hasOtherChanges = true;
            break;
        }
    }
    return hasOtherChanges;
}

patch(PosOrder.prototype, {

    setup(vals) {
        super.setup(vals);
        console.log("this Setup original");
        this.ticket_number = vals.ticket_number ;
        this.locked = ('locked' in vals) ? vals.locked : false;
        console.log("vals",vals);

    },
    lock() {
        this.locked = true;
      },

    isLocked() {
        console.log("🔒 Check isLocked ->", this.locked);
        return this.locked === true;
    },


    lockOrder() {
        this.locked = true;
    },

    /* This function is called after the order has been successfully sent to the preparation tool(s). */
    // @Override
    updateLastOrderChange() {

        const res = super.updateLastOrderChange();
    },

    //@override
    removeOrderline(line) {
        const pos = this.pos;
        const currentUser = pos.cashier;

        const linesToRemove = line.getAllLinesInCombo();
        for (const lineToRemove of linesToRemove) {
            //this.linesToRemove.push({...lineToRemove, cashier: currentUser});
            //console.log("this.linesToRemove :  ", this.linesToRemove);
            this._unlinkOrderline(lineToRemove);
            if (lineToRemove.refunded_orderline_id in this.pos.toRefundLines) {
                delete this.pos.toRefundLines[lineToRemove.refunded_orderline_id];
            }

        }

        const isAdmin = currentUser.role === "admin" || currentUser.role === "manager";
        if (!isAdmin) {
            if(!checkForChanges()){
                setTimeout(() => {
                    const numpadButtons = document.querySelectorAll(".numpad button");
                    const selectedOrderLines = document.querySelectorAll(".orderline.selected");
                    selectedOrderLines.forEach(el => {
                        el.classList.remove("selected");
                    });
                    numpadButtons.forEach(button => {
                        button.disabled = true;
                        button.style.pointerEvents = "none";
                        console.log('disabled  after removeOrderline')
                    });
                }, 200);
            } else if(this.selected_orderline){
                this.selected_orderline.set_selected(false);
                this.selected_orderline = undefined;
            }
        } else {
            this.select_orderline(this.get_last_orderline());
        }
        return true;
    },
});