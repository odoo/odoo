/* eslint { "no-restricted-syntax": [ "error", {
    "selector": "MemberExpression[object.type=ThisExpression][property.name=pos]",
    "message": "Using this.pos in models is deprecated and about to be removed, for any question ask PoS team." }]}*/

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    //@override
    select_orderline(orderline) {
        super.select_orderline(...arguments);
        if (
            orderline &&
            this.config.down_payment_product_id &&
            orderline.product_id.id === this.config.down_payment_product_id.id
        ) {
            this.pos.numpadMode = "price"; // eslint-disable-line
        }
    },
    //@override
    _get_ignored_product_ids_total_discount() {
        const productIds = super._get_ignored_product_ids_total_discount(...arguments);
        if (this.config.down_payment_product_id) {
            productIds.push(this.config.down_payment_product_id.id);
        }
        return productIds;
    },
});
