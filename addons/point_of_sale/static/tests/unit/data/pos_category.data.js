import { models } from "@web/../tests/web_test_helpers";

export class PosCategory extends models.ServerModel {
    _name = "pos.category";

    _load_pos_data_fields() {
        return [
            "id",
            "name",
            "parent_id",
            "child_ids",
            "write_date",
            "has_image",
            "color",
            "sequence",
            "hour_until",
            "hour_after",
        ];
    }

    _records = [
        {
            id: 1,
            name: "Category 1",
            parent_id: false,
            child_ids: [],
            has_image: false,
            color: 0,
            sequence: 0,
            hour_until: 0.0,
            hour_after: 24.0,
        },
        {
            id: 2,
            name: "Category 2",
            parent_id: false,
            child_ids: [],
            has_image: false,
            color: 0,
            sequence: 0,
            hour_until: 0.0,
            hour_after: 24.0,
        },
    ];
}
