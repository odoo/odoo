/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(PosStore.prototype, {
    async setTable(table, orderUid = null) {
        await super.setTable(...arguments);
        this.updateRewards();
    },
    getCouponFromOrders(orders){
        const uuidCoupon = {};
        orders.forEach(order => {
            order.lines.forEach(line => {
                if (line.is_reward_line) {
                    const { coupon_id } = line;
                    const { points, program_id, partner_id, code } = coupon_id;
                    uuidCoupon[line.uuid] = {
                        points,
                        program_id: program_id?.id,
                        code,
                        partner_id: partner_id?.id,
                    }
                }
            })
        });
        return uuidCoupon;
    },
    getSyncAllOrdersContext(orders, options = {}) {
        const context = super.getSyncAllOrdersContext(...arguments);
        context.coupons = this.getCouponFromOrders(orders);
        return context;
    }
});
