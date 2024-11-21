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
});
