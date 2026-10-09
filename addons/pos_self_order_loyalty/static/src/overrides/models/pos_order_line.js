import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline.prototype, {
    get countInLineNotSend() {
        return (
            super.countInLineNotSend &&
            (!this.is_reward_line || this.reward_id.reward_type != "discount")
        );
    },
    get imageUrl() {
        if (this.is_reward_line && this.reward_id.reward_type === "discount") {
            return `/web/image/loyalty.reward/${this.reward_id.id}/image_512?unique=${this.reward_id.write_date}`;
        }
        return `/web/image/product.product/${this.product_id.id}/image_512?unique=${this.product_id.write_date}`;
    },
});
