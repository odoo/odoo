/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { Orderline } from "@point_of_sale/app/store/models";

patch(Orderline.prototype, {
    /**
     * @returns {boolean}
     */
    isGiftCardOrEWalletReward() {
        const coupon = this.pos.couponCache[this.coupon_id];
        if (!coupon || !this.is_reward_line) {
            return false;
        }
        const program = this.pos.program_by_id[coupon.program_id];
        return ["ewallet", "gift_card"].includes(program.program_type);
    },
    /**
     * @returns {string}
     */
    getGiftCardOrEWalletBalance() {
        const coupon = this.pos.couponCache[this.coupon_id];
        return this.env.utils.formatCurrency(coupon?.balance || 0);
    },
    /**
     * override
     */
    getDisplayClasses() {
        return {
            ...super.getDisplayClasses(),
            "fst-italic":
                this.pos.mainScreen.component.name === "ProductScreen" && this.is_reward_line,
        };
    },
});
