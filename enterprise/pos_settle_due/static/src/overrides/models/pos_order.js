import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/app/models/pos_order";

patch(PosOrder.prototype, {
    // @Override
    set_to_invoice(to_invoice) {
        if (this.is_settling_account && this.lines.length === 0) {
            super.set_to_invoice(false);
        } else {
            super.set_to_invoice(to_invoice);
        }
    },

    get_change() {
        if (!this.is_settling_account) {
            return super.get_change();
        }

        const shouldRound = this.payment_ids.some((p) => this.shouldRound(p.payment_method_id));

        const remaining = shouldRound
            ? this.getRoundedRemaining(this.config.rounding_method, this.taxTotals.order_remaining)
            : this.taxTotals.order_remaining;

        return -this.taxTotals.order_sign * remaining;
    },
});
