import { models } from "@web/../tests/web_test_helpers";

export class AccountTaxGroup extends models.ServerModel {
    _name = "account.tax.group";

    _load_pos_data_fields() {
        return ["id", "name", "pos_receipt_label"];
    }

    _load_pos_data_dependencies() {
        return [];
    }

    _records = [
        {
            id: 1,
            name: "Tax 15%",
            pos_receipt_label: false,
            write_date: "2025-01-01 10:00:00",
        },
        {
            id: 2,
            name: "Tax 0%",
            pos_receipt_label: false,
            write_date: "2025-01-01 10:00:00",
        },
        {
            id: 3,
            name: "Tax 25%",
            pos_receipt_label: false,
        },
        {
            id: 4,
            name: "No group",
            pos_receipt_label: false,
        },
    ];
}
