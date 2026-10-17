import { patch } from "@web/core/utils/patch";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";

patch(PosOrderline.prototype, {
    canBeMergedWith(orderline) {
        if (this._mainLine || this.order_id._creatingDepositLine) {
            return false;
        }
        return super.canBeMergedWith(orderline);
    },

    setQuantity(quantity, keep_price) {
        const order = this.order_id;
        if (order._depositSyncing) {
            return super.setQuantity(quantity, keep_price);
        }
        const root = (this._mainLine || this).parentLine;
        const newQty =
            typeof quantity === "number" ? quantity : parseFloat("" + (quantity ? quantity : 0));

        order._depositSyncing = true;
        try {
            let result;
            if (root === this || !Number.isFinite(newQty)) {
                result = super.setQuantity(quantity, keep_price);
            } else if (!this.qty) {
                result = root.setQuantity(newQty);
            } else {
                result = root.setQuantity(root.qty * (newQty / this.qty));
            }
            if (result === true) {
                for (const line of root.getAllLinesInCombo()) {
                    const deposit = line._depositLine;
                    if (
                        deposit &&
                        this.order_id.lines.includes(deposit) &&
                        deposit.qty !== line.qty
                    ) {
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
