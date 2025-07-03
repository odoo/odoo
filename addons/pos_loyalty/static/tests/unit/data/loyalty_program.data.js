import { patch } from "@web/core/utils/patch";
import { hootPosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { models } from "@web/../tests/web_test_helpers";

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

patch(hootPosModels, [...hootPosModels, LoyaltyProgram]);
