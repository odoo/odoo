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

    _records = [
        {
            id: 1,
            program_id: 1,
            valid_product_ids: [5],
            any_product: true,
            currency_id: 1,
            reward_point_amount: 1,
            reward_point_split: true,
            reward_point_mode: "order",
            minimum_qty: 0,
            minimum_amount: 0,
            minimum_amount_tax_mode: "incl",
            mode: "auto",
            code: false,
        },
        {
            id: 2,
            program_id: 2,
            valid_product_ids: [5],
            any_product: true,
            currency_id: 1,
            reward_point_amount: 1,
            reward_point_split: true,
            reward_point_mode: "order",
            minimum_qty: 3,
            minimum_amount: 40,
            minimum_amount_tax_mode: "excl",
            mode: "auto",
            code: false,
        },
        {
            id: 3,
            program_id: 6,
            valid_product_ids: [5],
            any_product: true,
            currency_id: 1,
            reward_point_amount: 1,
            reward_point_split: true,
            reward_point_mode: "order",
            minimum_qty: 3,
            minimum_amount: 40,
            minimum_amount_tax_mode: "excl",
            mode: "with_code",
            code: "EXPIRED",
        },
    ];
}

patch(hootPosModels, [...hootPosModels, LoyaltyRule]);
