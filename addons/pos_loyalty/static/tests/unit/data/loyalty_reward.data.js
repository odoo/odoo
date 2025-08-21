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

    _records = [
        {
            id: 1,
            description: "10% Discount",
            program_id: 1,
            reward_type: "discount",
            required_points: 10,
            clear_wallet: false,
            currency_id: 1,
            discount: 10,
            discount_mode: "percent",
            discount_applicability: "order",
            all_discount_product_ids: [],
            is_global_discount: true,
            discount_max_amount: 0,
            discount_line_product_id: false,
            reward_product_id: false,
            multi_product: false,
            reward_product_ids: [5],
            reward_product_qty: 1,
            reward_product_uom_id: false,
            reward_product_domain: "[]",
        },
        {
            id: 2,
            description: "20% Discount",
            program_id: 2,
            reward_type: "product",
            required_points: 10,
            clear_wallet: false,
            currency_id: 1,
            discount: 0,
            discount_mode: "percent",
            discount_applicability: "order",
            all_discount_product_ids: [],
            is_global_discount: true,
            discount_max_amount: 0,
            discount_line_product_id: false,
            reward_product_id: false,
            multi_product: false,
            reward_product_ids: [5],
            reward_product_qty: 1,
            reward_product_uom_id: false,
            reward_product_domain: "[]",
        },
    ];
}

patch(hootPosModels, [...hootPosModels, LoyaltyReward]);
