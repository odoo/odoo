import { LoyaltyReward } from "@pos_loyalty/app/models/loyalty_reward";
import { patch } from "@web/core/utils/patch";

patch(LoyaltyReward.prototype, {
    _isDiscountableLine(line) {
        return !line.product_id.product_tmpl_id.is_deposit && super._isDiscountableLine(line);
    },
});
