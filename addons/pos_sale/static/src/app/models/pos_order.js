import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    //@override
    _getIgnoredProductIdsTotalDiscount() {
        const productIds = super._getIgnoredProductIdsTotalDiscount(...arguments);
        if (this.config.down_payment_product_id) {
            productIds.push(this.config.down_payment_product_id.id);
        }
        return productIds;
    },
    get hasPrePaidSOLine() {
        return this.payment_ids.some((payment) => payment.payment_method_id.use_sale_order_payment);
    },
    selectOrderline(line) {
        if (line?.sale_order_origin_id?.amount_unpaid === 0) {
            return super.selectOrderline();
        }
        return super.selectOrderline(line);
    },
});
