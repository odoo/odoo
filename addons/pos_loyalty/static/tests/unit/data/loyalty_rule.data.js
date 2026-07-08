import { patch } from "@web/core/utils/patch";
import { hootPosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { models } from "@web/../tests/web_test_helpers";

export class LoyaltyRule extends models.ServerModel {
    _name = "loyalty.rule";

    _load_pos_data_fields() {
        return [
            "program_id",
            "currency_id",
            "product_domain",
            "product_ids",
            "reward_point_amount",
            "reward_point_split",
            "reward_point_mode",
            "minimum_qty",
            "minimum_amount",
            "product_category_id",
            "minimum_amount_tax_mode",
            "mode",
            "code",
        ];
    }

    _records = [
        {
            id: 1,
            program_id: 1,
            currency_id: 1,
            product_category_id: 1,
            reward_point_amount: 1,
            reward_point_split: true,
            reward_point_mode: "order",
            minimum_qty: 0,
            minimum_amount: 0,
            product_domain: "[]",
            minimum_amount_tax_mode: "incl",
            mode: "auto",
            code: false,
        },
        {
            id: 2,
            program_id: 2,
            currency_id: 1,
            reward_point_amount: 1,
            reward_point_split: true,
            reward_point_mode: "order",
            minimum_qty: 3,
            product_domain: "[]",
            minimum_amount: 40,
            minimum_amount_tax_mode: "excl",
            mode: "auto",
            code: false,
        },
        {
            id: 3,
            program_id: 6,
            currency_id: 1,
            reward_point_amount: 1,
            reward_point_split: true,
            product_domain: "[]",
            reward_point_mode: "order",
            minimum_qty: 3,
            minimum_amount: 40,
            minimum_amount_tax_mode: "excl",
            mode: "with_code",
            code: "EXPIRED",
        },
        {
            id: 4,
            program_id: 7,
            currency_id: 1,
            reward_point_amount: 1,
            reward_point_split: false,
            reward_point_mode: "unit",
            minimum_qty: 1,
            product_domain: "[]",
            minimum_amount: 0,
            minimum_amount_tax_mode: "incl",
            mode: "auto",
        },
        {
            id: 5,
            program_id: 8,
            currency_id: 1,
            reward_point_amount: 1,
            reward_point_split: false,
            reward_point_mode: "unit",
            minimum_qty: 1,
            product_domain: "[]",
            minimum_amount: 0,
            minimum_amount_tax_mode: "incl",
            mode: "auto",
        },
    ];
}

patch(hootPosModels, [...hootPosModels, LoyaltyRule]);
