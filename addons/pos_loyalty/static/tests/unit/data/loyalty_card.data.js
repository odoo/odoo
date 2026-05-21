import { patch } from "@web/core/utils/patch";
import { hootPosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { models } from "@web/../tests/web_test_helpers";

export class LoyaltyCard extends models.ServerModel {
    _name = "loyalty.card";

    _load_pos_data_fields() {
        return ["partner_id", "code", "points", "program_id", "expiration_date"];
    }

    _records = [
        {
            // Loyalty card for partner 3 (Administrator) with 50 points
            id: 1,
            program_id: 1,
            partner_id: 3,
            points: 50,
            code: "LOYAL001",
            expiration_date: false,
        },
        {
            // Loyalty card for partner 4 (User1) with 5 points (not enough for reward)
            id: 2,
            program_id: 1,
            partner_id: 4,
            points: 5,
            code: "LOYAL002",
            expiration_date: false,
        },
        {
            // Coupon card with 1 point (enough for coupon program reward)
            id: 3,
            program_id: 4,
            partner_id: false,
            points: 1,
            code: "COUPON001",
            expiration_date: false,
        },
    ];
}

patch(hootPosModels, [...hootPosModels, LoyaltyCard]);
