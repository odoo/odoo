import { patch } from "@web/core/utils/patch";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";

patch(PosOrderline.prototype, {
    get_full_product_name() {
        if (this.product_id.alternative_name) {
            return this.product_id.alternative_name;
        }
        return super.get_full_product_name();
    },
});
