import { patch } from "@web/core/utils/patch";
import { PosPreset } from "@point_of_sale/../tests/unit/data/pos_preset.data";

patch(PosPreset.prototype, {
    _load_pos_data_fields() {
        return [...super._load_pos_data_fields(), "mail_template_id"];
    },
});

PosPreset._records = [
    ...PosPreset._records,
    {
        id: 10,
        name: "Self-Takeout",
        pricelist_id: false,
        fiscal_position_id: false,
        is_return: false,
        color: 0,
        has_image: false,
        write_date: "2025-07-21 12:46:07",
        identification: "none",
        use_timing: false,
        slots_per_interval: 5,
        interval_time: 20,
        attendance_ids: [],
        available_in_self: true,
        service_at: "table",
    },
];
