import { models } from "@web/../tests/web_test_helpers";

export class PosNote extends models.ServerModel {
    _name = "pos.note";

    _load_pos_data_fields() {
        return ["name", "color"];
    }

    _load_pos_data_dependencies() {
        return [];
    }

    _records = [
        {
            id: 1,
            name: "Wait",
            color: 0,
            write_date: "2025-01-01 10:00:00",
        },
        {
            id: 2,
            name: "To Serve",
            color: 0,
            write_date: "2025-01-01 10:00:00",
        },
        {
            id: 3,
            name: "Emergency",
            color: 0,
            write_date: "2025-01-01 10:00:00",
        },
        {
            id: 4,
            name: "No Dressing",
            color: 0,
            write_date: "2025-01-01 10:00:00",
        },
    ];
}
