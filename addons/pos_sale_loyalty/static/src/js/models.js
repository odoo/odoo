/** @odoo-module alias=pos_sale_loyalty.models **/


import { Orderline } from 'point_of_sale.models';
import Registries from 'point_of_sale.Registries';

export const PosSaleLoyaltyOrderline = (Orderline) => class PosSaleLoyaltyOrderline extends Orderline {
    //@override
    ignoreLoyaltyPoints(args) {
        if (this.sale_order_origin_id) {
            return true;
        }
        return super.ignoreLoyaltyPoints(args);
    }
    //@override
    setQuantityFromSOL(saleOrderLine) {
        // we need to consider reward product such as discount in a quotation
        if (saleOrderLine.reward_id) {
            this.set_quantity(saleOrderLine.product_uom_qty);
        } else {
            super.setQuantityFromSOL(...arguments);
        }
    }
};

Registries.Model.extend(Orderline, PosSaleLoyaltyOrderline);
