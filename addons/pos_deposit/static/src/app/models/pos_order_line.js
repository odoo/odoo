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
            const comboParent = mainLine.combo_parent_id;
            if (comboParent) {
                const qtyPerParent =
                    comboParent.qty && mainLine.qty ? mainLine.qty / comboParent.qty : 1;
                return comboParent.setQuantity(
                    (parseFloat(quantity) || 0) / qtyPerParent,
                    keep_price
                );
            }
            return mainLine.setQuantity(quantity, keep_price);
        }
        const result = super.setQuantity(quantity, keep_price);
        if (result === true && this.depositLine && this.depositLine.qty !== this.qty) {
            this.depositLine.setQuantity(this.qty);
        }
        return result;
    },

    get isValidForRefund() {
        return super.isValidForRefund && !this.deposit_main_line_id;
    },

    get prepQty() {
        return this.product_id.product_tmpl_id.is_deposit ? this.qty : super.prepQty;
    },
});
