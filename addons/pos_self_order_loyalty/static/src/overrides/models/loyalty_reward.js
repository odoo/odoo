import { patch } from "@web/core/utils/patch";
import { LoyaltyReward } from "@pos_loyalty/app/models/loyalty_reward";

patch(LoyaltyReward.prototype, {
    get imageUrl() {
        return (
            this._has_image &&
            `/web/image/loyalty.reward/${this.id}/image_512?unique=${this.write_date}`
        );
    },
});
