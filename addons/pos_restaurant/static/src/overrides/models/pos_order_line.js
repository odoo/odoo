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
            this.setDirty();
            this.skip_change = !this.skip_change;
            // Update skip_change for combo lines
            for (const comboLine of this.combo_line_ids) {
                if (comboLine.uiState.hasChange || comboLine.skip_change) {
                    comboLine.setDirty();
                    comboLine.skip_change = this.skip_change;
                }
            }
            // update with the combo parent if applicable
            if (this.combo_parent_id) {
                this.updateParentSkipChange(this.combo_parent_id);
            }
        }
    },
    updateParentSkipChange(parentOrderline) {
        let allLinesSynced = true;
        for (const comboLine of parentOrderline.combo_line_ids) {
            if (comboLine.uiState.hasChange || comboLine.skip_change) {
                if (comboLine.skip_change !== this.skip_change) {
                    allLinesSynced = false;
                    break;
                }
            }
        }
        if (allLinesSynced) {
            this.setDirty();
            parentOrderline.skip_change = this.skip_change;
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
