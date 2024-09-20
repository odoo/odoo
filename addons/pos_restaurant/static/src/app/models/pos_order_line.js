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
            // update with the combo parent if applicable
            if (this.combo_parent_id) {
                const parent = this.combo_parent_id;
                parent.skip_change = this.skip_change;
                this.updateChildrenSkipChange(parent);
            }
            if (this.combo_line_ids) {
                this.updateChildrenSkipChange(this);
            }
        }
    },
    updateChildrenSkipChange(parentOrderline) {
        for (const comboLine of parentOrderline.combo_line_ids) {
            if (comboLine.uiState.hasChange || comboLine.skip_change) {
                comboLine.skip_change = this.skip_change;
            }
        }
    },
    showSkipChange() {
        return this.skip_change && !this.uiState.hideSkipChangeClass && !this.origin_order_id;
    },
    getDisplayClasses() {
        return {
            ...super.getDisplayClasses(),
            "has-change": this.uiState.hasChange && this.config.module_pos_restaurant,
            "skip-change": this.showSkipChange() && this.config.module_pos_restaurant,
        };
    },
});
