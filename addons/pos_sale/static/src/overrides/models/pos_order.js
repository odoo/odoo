import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    //@override
    _get_ignored_product_ids_total_discount() {
        const productIds = super._get_ignored_product_ids_total_discount(...arguments);
        if (this.config.down_payment_product_id) {
            productIds.push(this.config.down_payment_product_id.id);
        }
        return productIds;
    },
    is_link_to_sale_order() {
        return this.lines.some(
            (l) => l.sale_order_origin_id || l.refunded_orderline_id?.sale_order_origin_id
        );
    },
    is_to_invoice() {
        if (this.is_link_to_sale_order()) {
            return true;
        }
        return super.is_to_invoice(...arguments);
    },
    set_to_invoice(to_invoice) {
        if (this.is_link_to_sale_order()) {
            this.assert_editable();
            this.to_invoice = true;
        }
        return super.set_to_invoice(...arguments);
    },
});
