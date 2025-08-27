import { models } from "@web/../tests/web_test_helpers";

export class AccountJournal extends models.ServerModel {
    _name = "account.journal";

    _load_pos_data_fields() {
        return [];
    }

    _load_pos_data_dependencies() {
        return [];
    }

    _records = [
        {
            id: 1,
            name: "Point of Sale",
            type: "sale",
            code: "POS",
            company_id: 250,
            write_date: "2025-01-01 10:00:00",
        },
    ];
}
