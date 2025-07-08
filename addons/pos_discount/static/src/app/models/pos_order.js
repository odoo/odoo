import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    getDiscountLine() {
        return this.lines?.find(
            (line) => line.product_id.id === this.config.discount_product_id?.id
        );
    },
});
