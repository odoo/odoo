import { models } from "@web/../tests/web_test_helpers";

export class PosNote extends models.ServerModel {
    _name = "pos.note";

    _load_pos_data_fields() {
        return ["name", "color"];
    }

    _records = [
        {
            id: 1,
            name: "Wait",
            color: 0,
        },
        {
            id: 2,
            name: "To Serve",
            color: 0,
        },
        {
            id: 3,
            name: "Emergency",
            color: 0,
        },
        {
            id: 4,
            name: "No Dressing",
            color: 0,
        },
    ];
}
