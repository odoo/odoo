/** @odoo-module **/

import OrderSummary from 'point_of_sale.OrderSummary';
import Registries from 'point_of_sale.Registries';

export const PosLoyaltyOrderSummary = (OrderSummary) => 
    class PosLoyaltyOrderSummary extends OrderSummary {
        getLoyaltyPoints() {
            const order = this.env.pos.get_order();
            return order.getLoyaltyPoints();
        }
    };

Registries.Component.extend(OrderSummary, PosLoyaltyOrderSummary)
