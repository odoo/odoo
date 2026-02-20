import { CartLines } from '@website_sale/js/cart_lines/cart_lines';
import { patch } from '@web/core/utils/patch';


patch(CartLines.prototype, {
    getLineProps(line) {
        return {
            ...super.getLineProps(line),
            isRewardLine: line.is_reward_line,
            showCouponCode: line.show_coupon_code,
            couponCode: line.coupon_code ?? false,
            couponExpirationDate: line.coupon_expiration_date ?? false,
            rewardType: line.reward_type ?? false,
        }
    },
});
