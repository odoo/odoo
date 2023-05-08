/** @odoo-module **/

import { Orderline } from "@point_of_sale/js/Screens/ProductScreen/Orderline";
import { patch } from "@web/core/utils/patch";

patch(Orderline.prototype, "pos_loyalty.Orderline", {
    get addedClasses() {
        return Object.assign(
            { "program-reward": this.props.line.is_reward_line },
            this._super(...arguments)
        );
    },
    _isGiftCardOrEWalletReward() {
        const coupon = this.env.pos.couponCache[this.props.line.coupon_id];
        if (coupon) {
            const program = this.env.pos.program_by_id[coupon.program_id];
            return (
                ["ewallet", "gift_card"].includes(program.program_type) &&
                this.props.line.is_reward_line
            );
        }
        return false;
    },
    _getGiftCardOrEWalletBalance() {
        const coupon = this.env.pos.couponCache[this.props.line.coupon_id];
        if (coupon) {
            return this.env.utils.formatCurrency(coupon.balance);
        }
        return this.env.utils.formatCurrency(0);
    },
});
