import { patch } from "@web/core/utils/patch";
import { PosOrderLine } from "@point_of_sale/../tests/unit/data/pos_order_line.data";

patch(PosOrderLine.prototype, {
    _load_pos_data_fields() {
        return [
            ...super._load_pos_data_fields(),
            "is_reward_line",
            "reward_id",
            "coupon_id",
            "reward_identifier_code",
            "points_cost",
        ];
    },
});
