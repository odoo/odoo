import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline.prototype, {
    //@override
    ignoreLoyaltyPoints(args) {
        if (this.sale_order_origin_id) {
            return true;
        }
        return super.ignoreLoyaltyPoints(args);
    },
});

patch(PosOrder.prototype, {
    isLineValidForLoyaltyPoints(line) {
        const result = super.isLineValidForLoyaltyPoints(line);
        return !line.sale_order_origin_id && result;
    },
});
