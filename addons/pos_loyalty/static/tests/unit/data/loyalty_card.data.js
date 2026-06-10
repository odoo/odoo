import { patch } from "@web/core/utils/patch";
import { hootPosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { models } from "@web/../tests/web_test_helpers";
import { uuidv4 } from "@point_of_sale/utils";

const { DateTime } = luxon;

export class LoyaltyCard extends models.ServerModel {
    _name = "loyalty.card";

    _load_pos_data_fields() {
        return [
            "partner_id",
            "code",
            "points",
            "program_id",
            "expiration_date",
            "write_date",
            "uuid",
            "source_pos_order_id",
            "_temp_points",
        ];
    }

    _records = [
        {
            id: 1,
            code: "CARD001",
            points: 10,
            partner_id: 1,
            program_id: 1,
            expiration_date: DateTime.now().plus({ days: 1 }).toISODate(),
            write_date: DateTime.now().minus({ days: 1 }).toFormat("yyyy-MM-dd HH:mm:ss"),
            uuid: "card-uuid-001",
        },
        {
            id: 2,
            code: "CARD002",
            points: 25,
            partner_id: 1,
            program_id: 2,
            expiration_date: DateTime.now().minus({ days: 1 }).toISODate(),
            write_date: DateTime.now().minus({ days: 2 }).toFormat("yyyy-MM-dd HH:mm:ss"),
            uuid: "card-uuid-002",
        },
        {
            id: 3,
            code: "CARD003",
            points: 15,
            partner_id: 3,
            program_id: 3,
            write_date: DateTime.now().toFormat("yyyy-MM-dd HH:mm:ss"),
            uuid: "card-uuid-003",
        },
        {
            id: 4,
            code: "CARD004",
            points: 3,
            partner_id: 1,
            program_id: 7,
            write_date: DateTime.now().minus({ days: 2 }).toFormat("yyyy-MM-dd HH:mm:ss"),
        },
    ];

    _generate_code() {
        return uuidv4().slice(9, 23);
    }
}

patch(hootPosModels, [...hootPosModels, LoyaltyCard]);
