import { patch } from "@web/core/utils/patch";
import {
    modelsToLoad,
    posModels,
    PosOrderLine,
    ProductProduct,
} from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { defineModels, models } from "@web/../tests/web_test_helpers";

export class LoyaltyProgram extends models.ServerModel {
    _name = "loyalty.program";

    _load_pos_data_fields() {
        return [
            "name",
            "trigger",
            "applies_on",
            "program_type",
            "pricelist_ids",
            "date_from",
            "date_to",
            "limit_usage",
            "max_usage",
            "is_nominative",
            "portal_visible",
            "portal_point_name",
            "trigger_product_ids",
            "rule_ids",
            "reward_ids",
        ];
    }
}

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

export class LoyaltyCard extends models.ServerModel {
    _name = "loyalty.card";

    _load_pos_data_fields() {
        return ["partner_id", "code", "points", "program_id", "expiration_date", "write_date"];
    }
}
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

patch(ProductProduct.prototype, {
    _load_pos_data_fields() {
        return [...super._load_pos_data_fields(), "all_product_tag_ids"];
    },
});

patch(modelsToLoad, [
    ...modelsToLoad,
    "loyalty.program",
    "loyalty.rule",
    "loyalty.reward",
    "loyalty.card",
]);
patch(posModels, [...posModels, LoyaltyProgram, LoyaltyRule, LoyaltyReward, LoyaltyCard]);
defineModels([LoyaltyProgram, LoyaltyRule, LoyaltyReward, LoyaltyCard]);
