import { patch } from "@web/core/utils/patch";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";

patch(PosOrderline.prototype, {
    get depositLine() {
        return this.deposit_line_ids[0];
    },

    canBeMergedWith(orderline) {
        return (
            !this.deposit_main_line_id &&
            !orderline.deposit_main_line_id &&
            super.canBeMergedWith(orderline)
        );
    },
    setQuantity(quantity, keep_price) {
        const mainLine = this.deposit_main_line_id;
        if (mainLine && mainLine.qty !== quantity) {
            const parent = mainLine.combo_parent_id;
            if (parent && quantity !== "remove") {
                const perParent = parent.qty && mainLine.qty ? mainLine.qty / parent.qty : 1;
                return parent.setQuantity((parseFloat(quantity) || 0) / perParent, keep_price);
            }
            return mainLine.setQuantity(quantity, keep_price);
        }
        const result = super.setQuantity(quantity, keep_price);
        if (result === true) {
            for (const line of [this, ...this.combo_line_ids]) {
                if (line.depositLine && line.depositLine.qty !== line.qty) {
                    line.depositLine.setQuantity(line.qty);
                }
            }
        }
        return result;
    },
});
