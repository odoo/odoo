/** @odoo-module alias=pos_sale_loyalty.models **/


import { Orderline } from '@point_of_sale/js/models';
import { patch } from "@web/core/utils/patch";

patch(Orderline.prototype, "pos_sale_loyalty.Orderline", {
    //@override
    ignoreLoyaltyPoints(args) {
        if (this.sale_order_origin_id) {
            return true;
        }
        return this._super(args);
    },
    //@override
    setQuantityFromSOL(saleOrderLine) {
        // we need to consider reward product such as discount in a quotation
        if (saleOrderLine.reward_id) {
            this.set_quantity(saleOrderLine.product_uom_qty);
        } else {
            this._super(...arguments);
        }
    },
});
