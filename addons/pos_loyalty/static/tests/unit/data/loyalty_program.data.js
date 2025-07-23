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

    _records = [
        {
            id: 1,
            name: "Loyalty Program",
            trigger: "auto",
            applies_on: "both",
            program_type: "loyalty",
            pricelist_ids: [],
            date_from: false,
            date_to: false,
            limit_usage: false,
            max_usage: 0,
            is_nominative: false,
            portal_visible: true,
            portal_point_name: "Points",
            trigger_product_ids: [],
            rule_ids: [],
            reward_ids: [],
        },
        {
            id: 2,
            name: "E-Wallet Program",
            trigger: "auto",
            applies_on: "future",
            program_type: "ewallet",
            pricelist_ids: [],
            date_from: false,
            date_to: false,
            limit_usage: false,
            max_usage: 0,
            is_nominative: false,
            portal_visible: true,
            portal_point_name: "E-Wallet Points",
            trigger_product_ids: [],
            rule_ids: [],
            reward_ids: [],
        },
        {
            id: 3,
            name: "Gift Card Program",
            trigger: "auto",
            applies_on: "future",
            program_type: "gift_card",
            pricelist_ids: [],
            date_from: false,
            date_to: false,
            limit_usage: false,
            max_usage: 0,
            is_nominative: false,
            portal_visible: true,
            portal_point_name: "Gift Card Points",
            trigger_product_ids: [],
            rule_ids: [],
            reward_ids: [],
        },
    ];
}

patch(hootPosModels, [...hootPosModels, LoyaltyProgram]);
