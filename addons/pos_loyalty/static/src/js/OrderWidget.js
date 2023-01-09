/** @odoo-module **/

import OrderWidget from "@point_of_sale/js/Screens/ProductScreen/OrderWidget";
import Registries from "@point_of_sale/js/Registries";

export const PosLoyaltyOrderWidget = (OrderWidget) =>
    class PosLoyaltyOrderWidget extends OrderWidget {
        getActiveProgramsAndRewards() {
            const order = this.env.pos.get_order();
            const activePrograms = Object.values(order.couponPointChanges).map(
                (pe) => this.env.pos.program_by_id[pe.program_id]
            );
            const seenRewards = new Set();
            const activeRewards = [];
            for (const line of order._get_reward_lines()) {
                const key =
                    line.reward_id + "-" + line.coupon_id + "-" + line.reward_identifier_code;
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
            const activeCoupons = order.codeActivatedCoupons.map((coupon) => {
                const program = this.env.pos.program_by_id[coupon.program_id];
                return {
                    programName: program.name,
                    code: coupon.code,
                };
            });
            return {
                activePrograms: [...new Set(activePrograms)],
                activeCoupons,
                activeRewards,
            };
        }
    };

Registries.Component.extend(OrderWidget, PosLoyaltyOrderWidget);
