import { models } from "@web/../tests/web_test_helpers";

export class PosPreset extends models.ServerModel {
    _name = "pos.preset";

    _load_pos_data_fields() {
        return [
            "id",
            "name",
            "pricelist_id",
            "fiscal_position_id",
            "is_return",
            "color",
            "has_image",
            "write_date",
            "identification",
            "use_timing",
            "slots_per_interval",
            "interval_time",
            "attendance_ids",
        ];
    }

    _records = [
        {
            id: 1,
            name: "In",
            pricelist_id: 1,
            fiscal_position_id: 1,
            is_return: false,
            color: 0,
            has_image: false,
            write_date: "2025-07-03 14:34:01",
            identification: "none",
            use_timing: false,
            slots_per_interval: 5,
            interval_time: 20,
            attendance_ids: [],
        },
        {
            id: 2,
            name: "Out",
            pricelist_id: false,
            fiscal_position_id: false,
            is_return: false,
            color: 0,
            has_image: false,
            write_date: "2025-07-03 14:34:07",
            identification: "none",
            use_timing: true,
            slots_per_interval: 5,
            interval_time: 20,
            attendance_ids: [],
            resource_calendar_id: 1,
        },
        {
            id: 3,
            name: "Name Required Preset",
            identification: "name",
            use_timing: false,
        },
        {
            id: 4,
            name: "Address Required Preset",
            identification: "address",
            use_timing: false,
        },
    ];
}
