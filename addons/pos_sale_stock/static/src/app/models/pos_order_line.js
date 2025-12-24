import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline.prototype, {
    setup(_defaultObj) {
        super.setup(...arguments);
        // It is possible that this orderline is initialized using server data,
        // meaning, it is loaded from localStorage or from server. This means
        // that some fields has already been assigned. Therefore, we only set the options
        // when the original value is falsy.
        if (this.sale_order_origin_id?.shipping_date) {
            this.order_id.shipping_date = this.sale_order_origin_id.shipping_date;
        }
    },
});
