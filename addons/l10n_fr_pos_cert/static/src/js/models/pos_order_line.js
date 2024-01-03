/** @odoo-module */

import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline.prototype, {
    can_be_merged_with(orderline) {
        if (!this.order_id.is_french_country()) {
            return super.can_be_merged_with(...arguments);
        }
        const order = this.order_id;
        const orderlines = order.lines;
        const lastOrderline = order.lines.at(orderlines.length - 1);

        if (lastOrderline.product_id.id !== orderline.product_id.id || lastOrderline.qty < 0) {
            return false;
        } else {
            return super.can_be_merged_with(...arguments);
        }
    },
});
