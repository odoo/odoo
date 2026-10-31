import { patch } from "@web/core/utils/patch";
import { LoyaltyReward } from "@pos_loyalty/app/models/loyalty_reward";

patch(LoyaltyReward.prototype, {
    get imageUrl() {
        return (
            (this._has_image &&
                `/web/image/loyalty.reward/${this.id}/image_512?unique=${this.write_date}`) ||
            (this.reward_type === "product" &&
                this.reward_product_ids.length == 1 &&
                `/web/image/product.product/${this.reward_product_ids[0].id}/image_512/?unique=${this.reward_product_ids[0].write_date}`)
        );
    },
});
