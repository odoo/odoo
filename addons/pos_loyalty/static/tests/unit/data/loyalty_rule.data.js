import { patch } from "@web/core/utils/patch";
import { hootPosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { models } from "@web/../tests/web_test_helpers";

export class LoyaltyRule extends models.ServerModel {
    _name = "loyalty.rule";

    _load_pos_data_fields() {
        return [
            "program_id",
            "valid_product_ids",
            "any_product",
            "currency_id",
            "reward_point_amount",
            "reward_point_split",
            "reward_point_mode",
            "minimum_qty",
            "minimum_amount",
            "minimum_amount_tax_mode",
            "mode",
            "code",
        ];
    }
}

patch(hootPosModels, [...hootPosModels, LoyaltyRule]);
