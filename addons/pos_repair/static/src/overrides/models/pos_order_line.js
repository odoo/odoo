import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline.prototype, {
    //@override
    setQuantityFromSOL(saleOrderLine) {
        if (saleOrderLine.is_repair_line) {
            this.setQuantity(saleOrderLine.product_uom_qty);
        } else {
            super.setQuantityFromSOL(...arguments);
        }
    },
});
