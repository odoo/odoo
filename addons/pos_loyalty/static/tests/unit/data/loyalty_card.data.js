import { patch } from "@web/core/utils/patch";
import { hootPosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { models } from "@web/../tests/web_test_helpers";

const { DateTime } = luxon;

export class LoyaltyCard extends models.ServerModel {
    _name = "loyalty.card";

    _load_pos_data_fields() {
        return ["partner_id", "code", "points", "program_id", "expiration_date", "write_date"];
    }

    _records = [
        {
            id: 1,
            partner_id: false,
            code: "CARD001",
            points: 10,
            expiration_date: DateTime.now().plus({ days: 1 }).toISODate(),
            write_date: DateTime.now().minus({ days: 1 }).toFormat("yyyy-MM-dd HH:mm:ss"),
        },
        {
            id: 2,
            partner_id: false,
            code: "CARD002",
            points: 25,
            expiration_date: DateTime.now().minus({ days: 1 }).toISODate(),
            write_date: DateTime.now().minus({ days: 2 }).toFormat("yyyy-MM-dd HH:mm:ss"),
        },
        {
            id: 3,
            partner_id: false,
            code: "CARD003",
            points: 15,
            write_date: DateTime.now().toFormat("yyyy-MM-dd HH:mm:ss"),
        },
    ];
}

patch(hootPosModels, [...hootPosModels, LoyaltyCard]);
