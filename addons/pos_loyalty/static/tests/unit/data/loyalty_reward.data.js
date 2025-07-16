import { patch } from "@web/core/utils/patch";
import { hootPosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { models } from "@web/../tests/web_test_helpers";

export class LoyaltyReward extends models.ServerModel {
    _name = "loyalty.reward";

    _load_pos_data_fields() {
        return [
            "description",
            "program_id",
            "reward_type",
            "required_points",
            "clear_wallet",
            "currency_id",
            "discount",
            "discount_mode",
            "discount_applicability",
            "all_discount_product_ids",
            "is_global_discount",
            "discount_max_amount",
            "discount_line_product_id",
            "reward_product_id",
            "multi_product",
            "reward_product_ids",
            "reward_product_qty",
            "reward_product_uom_id",
            "reward_product_domain",
        ];
    }
}

patch(hootPosModels, [...hootPosModels, LoyaltyReward]);
