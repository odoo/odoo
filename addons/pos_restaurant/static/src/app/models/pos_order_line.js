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
    toggleSkipChange() {
        if (this.uiState.hasChange || this.skip_change) {
            this.setDirty();
            this.skip_change = !this.skip_change;
        }
    },
    getDisplayClasses() {
        return {
            ...super.getDisplayClasses(),
            "has-change": this.uiState.hasChange && this.config.module_pos_restaurant,
            "skip-change": this.skip_change && this.config.module_pos_restaurant,
        };
    },
});
