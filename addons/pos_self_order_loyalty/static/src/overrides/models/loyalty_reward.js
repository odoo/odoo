import { patch } from "@web/core/utils/patch";
import { LoyaltyReward } from "@pos_loyalty/app/models/loyalty_reward";

patch(LoyaltyReward.prototype, {
    get requiredPointsToString() {
        return `${this.required_points} ${this.program_id.portal_point_name}`;
    },
});
