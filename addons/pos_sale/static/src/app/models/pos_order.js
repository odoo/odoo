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
    get hasPrePaidSOPayment() {
        return this.payment_ids.some((payment) => payment.payment_method_id.use_sale_order_payment);
    },
    /**
     * Ids of the accounting payments already settled by a payment line of this order,
     * so settling the same sale order twice does not pay it twice.
     *
     * @returns {Set<number>}
     */
    get settledSOAccountPaymentIds() {
        const settled = new Set();
        for (const payment of this.payment_ids) {
            if (payment.online_account_payment_id) {
                settled.add(payment.online_account_payment_id.id);
            }
        }
        return settled;
    },
    selectOrderline(line) {
        // Lines settled from a sale order paid online cannot be edited: the amount is
        // already fixed by the payment the customer made on the sale order.
        if (line?.sale_order_origin_id && this.hasPrePaidSOPayment) {
            return super.selectOrderline();
        }
        return super.selectOrderline(line);
    },
});
