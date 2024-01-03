/** @odoo-module */

import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline.prototype, {
    setup() {
        super.setup(...arguments);
        this.note = this.note || "";
    },
    //@override
    clone() {
        const orderline = super.clone(...arguments);
        orderline.note = this.note;
        return orderline;
    },
    get_line_diff_hash() {
        if (this.getNote()) {
            return this.id + "|" + this.getNote();
        } else {
            return "" + this.id;
        }
    },
    toggleSkipChange() {
        if (this.uiState.hasChange || this.skip_change) {
            this.skip_change = !this.skip_change;
        }
    },
    getDisplayClasses() {
        return {
            ...super.getDisplayClasses(),
            "has-change text-success border-start border-success border-4":
                this.uiState.hasChange && this.config.module_pos_restaurant,
            "skip-change text-primary border-start border-primary border-4":
                this.skip_change && this.config.module_pos_restaurant,
        };
    },
});
