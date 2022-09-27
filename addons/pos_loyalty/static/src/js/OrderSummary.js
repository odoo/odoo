/** @odoo-module **/

import OrderSummary from 'point_of_sale.OrderSummary';
import Registries from 'point_of_sale.Registries';

export const PosLoyaltyOrderSummary = (OrderSummary) => 
    class PosLoyaltyOrderSummary extends OrderSummary {
        getActiveRewards() {
            const order = this.env.pos.get_order();
            const seenRewards = new Set();
            const activeRewards = [];
            for (const line of order._get_reward_lines()) {
                const key = line.reward_id + '-' + line.coupon_id + '-' + line.reward_identifier_code;
                if (seenRewards.has(key)) {
                    continue;
                }
                seenRewards.add(key);
                const dbCoupon = this.env.pos.couponCache[line.coupon_id];
                const couponCode = dbCoupon ? dbCoupon.code : false;
                activeRewards.push({
                    id: line.cid,
                    name: line.get_product().display_name,
                    code: couponCode,
                });
            }
            return {
                activeRewards,
            }
        }

        getLoyaltyPoints() {
            const order = this.env.pos.get_order();
            return order.getLoyaltyPoints();
        }
    };

Registries.Component.extend(OrderSummary, PosLoyaltyOrderSummary)
