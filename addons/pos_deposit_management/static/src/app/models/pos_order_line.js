import { patch } from "@web/core/utils/patch";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";

patch(PosOrderline.prototype, {
    canBeMergedWith(orderline) {
        if (this.deposit_main_line_id || this.order_id._creatingDepositLine) {
            return false;
        }
        return super.canBeMergedWith(orderline);
    },

    setQuantity(quantity, keep_price) {
        const order = this.order_id;
        if (order._depositSyncing) {
            return super.setQuantity(quantity, keep_price);
        }

        const mainLine = this.deposit_main_line_id;
        if (mainLine) {
            const parent = mainLine.combo_parent_id;
            if (parent) {
                const newQty = typeof quantity === "number" ? quantity : parseFloat(quantity) || 0;
                const perParent = parent.qty && mainLine.qty ? mainLine.qty / parent.qty : 1;
                return parent.setQuantity(newQty / perParent, keep_price);
            }
            return mainLine.setQuantity(quantity, keep_price);
        }

        order._depositSyncing = true;
        try {
            const result = super.setQuantity(quantity, keep_price);
            if (result === true) {
                for (const line of [this, ...(this.combo_line_ids || [])]) {
                    const deposit = line.deposit_line_ids?.[0];
                    if (deposit && deposit.qty !== line.qty) {
                        deposit.setQuantity(line.qty);
                    }
                }
            }
            return result;
        } finally {
            order._depositSyncing = false;
        }
    },
});
