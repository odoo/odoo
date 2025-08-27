import { models } from "@web/../tests/web_test_helpers";

export class IrModuleModule extends models.ServerModel {
    _name = "ir.module.module";

    _load_pos_data_fields() {
        return ["id", "name", "state"];
    }

    _load_pos_data_dependencies() {
        return [];
    }

    _records = [
        {
            id: 901,
            name: "pos_settle_due",
            state: "installed",
            write_date: "2025-01-01 10:00:00",
        },
    ];
}
