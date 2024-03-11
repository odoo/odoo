/** @odoo-module **/

import Orderline from 'point_of_sale.Orderline';
import Registries from 'point_of_sale.Registries';

export const PosLoyaltyOrderline = (Orderline) =>
    class extends Orderline{
        get addedClasses() {
            return Object.assign({'program-reward': this.props.line.is_reward_line}, super.addedClasses);
        }
        _isGiftCardOrEWalletReward() {
            const coupon = this.env.pos.couponCache[this.props.line.coupon_id];
            if (coupon) {
                const program = this.env.pos.program_by_id[coupon.program_id]
                return ['ewallet', 'gift_card'].includes(program.program_type) && this.props.line.is_reward_line;
            }
            return false;
        }
        _getGiftCardOrEWalletBalance() {
            const coupon = this.env.pos.couponCache[this.props.line.coupon_id];
            if (coupon) {
                return this.env.pos.format_currency(coupon.balance);
            }
            return this.env.pos.format_currency(0);
        }
    };

Registries.Component.extend(Orderline, PosLoyaltyOrderline);
