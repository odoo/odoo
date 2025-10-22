import { models } from "@web/../tests/web_test_helpers";

export class AccountFiscalPosition extends models.ServerModel {
    _name = "account.fiscal.position";

    _load_pos_data_fields() {
        return ["id", "name", "display_name", "tax_map", "tax_ids"];
    }

    _records = [
        {
            id: 1,
            name: "Domestic",
            display_name: "Domestic",
            tax_ids: [1],
        },
        {
            id: 2,
            name: "No tax fp",
            display_name: "No tax fp",
        },
    ];
}
