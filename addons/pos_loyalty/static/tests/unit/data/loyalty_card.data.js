import { patch } from "@web/core/utils/patch";
import { hootPosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { models } from "@web/../tests/web_test_helpers";

export class LoyaltyCard extends models.ServerModel {
    _name = "loyalty.card";

    _load_pos_data_fields() {
        return ["partner_id", "code", "points", "program_id", "expiration_date", "write_date"];
    }
}

patch(hootPosModels, [...hootPosModels, LoyaltyCard]);
