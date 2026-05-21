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
            "product_ids",
            "product_category_id",
            "product_tag_id",
            "reward_point_mode",
            "reward_point_amount",
            "reward_point_split",
            "minimum_qty",
            "minimum_amount",
            "minimum_amount_tax_mode",
            "mode",
            "code",
            "promo_barcode",
        ];
    }

    _records = [
        {
            // Rule for Loyalty Program (id=1): 1 point per unit paid
            id: 1,
            program_id: 1,
            any_product: true,
            product_ids: [],
            reward_point_mode: "unit",
            reward_point_amount: 1,
            reward_point_split: false,
            minimum_qty: 1,
            minimum_amount: 0,
            minimum_amount_tax_mode: "incl",
            mode: "auto",
            code: false,
            valid_product_ids: [],
        },
        {
            // Rule for Promotion (id=2): minimum $50 order, 1 point per order
            id: 2,
            program_id: 2,
            any_product: true,
            product_ids: [],
            reward_point_mode: "order",
            reward_point_amount: 1,
            reward_point_split: false,
            minimum_qty: 0,
            minimum_amount: 50,
            minimum_amount_tax_mode: "incl",
            mode: "auto",
            code: false,
            valid_product_ids: [],
        },
        {
            // Rule for Promo Code (id=3): with code "SAVE10"
            id: 3,
            program_id: 3,
            any_product: true,
            product_ids: [],
            reward_point_mode: "order",
            reward_point_amount: 1,
            reward_point_split: false,
            minimum_qty: 0,
            minimum_amount: 0,
            minimum_amount_tax_mode: "incl",
            mode: "with_code",
            code: "SAVE10",
            valid_product_ids: [],
        },
        {
            // Rule for Buy X Get Y (id=5): buy 2 of product 5, get 1 free
            id: 5,
            program_id: 5,
            any_product: false,
            product_ids: [5],
            reward_point_mode: "unit",
            reward_point_amount: 1,
            reward_point_split: false,
            minimum_qty: 2,
            minimum_amount: 0,
            minimum_amount_tax_mode: "incl",
            mode: "auto",
            code: false,
            valid_product_ids: [5],
        },
        {
            // Rule for Gift Card (id=6): 1 point per $10 spent on gift cards
            id: 6,
            program_id: 6,
            any_product: false,
            product_ids: [20], // Assuming product 20 is the gift card
            reward_point_mode: "amount",
            reward_point_amount: 1,
            reward_point_split: false,
            minimum_qty: 0,
            minimum_amount: 10,
            minimum_amount_tax_mode: "incl",
            mode: "auto",
            code: false,
            valid_product_ids: [20],
        },
    ];
}

patch(hootPosModels, [...hootPosModels, LoyaltyRule]);
