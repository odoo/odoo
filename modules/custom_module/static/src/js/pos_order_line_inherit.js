/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";

patch(PosOrderline.prototype, {
    setup(attributes) {
        super.setup(attributes);
        this.locked = ('locked' in attributes) ? attributes.locked : false;
    },
    isLocked() {
        return this.locked === true;
    },

    lockLine() {
        this.locked = true;
    },

    unlockLine() {
        this.locked = false;
    },


});
