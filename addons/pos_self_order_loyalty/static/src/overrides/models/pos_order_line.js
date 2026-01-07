import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline.prototype, {
    initState() {
        super.initState();
        this.uiState = {
            rewardCode: "",
            ...this.uiState,
        };
    },
    get countInLineNotSend() {
        return super.countInLineNotSend && (!this.is_reward_line || this.reward_id.reward_type != "discount");
    },
});