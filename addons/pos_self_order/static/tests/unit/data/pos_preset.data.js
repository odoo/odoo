import { patch } from "@web/core/utils/patch";
import { PosPreset } from "@point_of_sale/../tests/unit/data/pos_preset.data";

patch(PosPreset.prototype, {
    _load_pos_data_fields() {
        return [
            ...super._load_pos_data_fields(),
            "mail_template_id",
            "available_in_self",
            "service_at",
        ];
    },
});

const presetDefaults = {
    pricelist_id: false,
    fiscal_position_id: false,
    is_return: false,
    color: 0,
    has_image: false,
    write_date: "2025-07-21 12:46:07",
    use_timing: false,
    slots_per_interval: 5,
    interval_time: 20,
    attendance_ids: [],
    available_in_self: true,
    mail_template_id: false,
};

PosPreset._records = [
    ...PosPreset._records.map((preset) => ({
        ...preset,
        available_in_self: true,
        service_at: preset.service_at || "counter",
        mail_template_id: false,
    })),
    {
        ...presetDefaults,
        id: 20,
        name: "Test-In",
        identification: "none",
        service_at: "table",
    },
    {
        ...presetDefaults,
        id: 21,
        name: "Test-Takeout",
        identification: "name",
        service_at: "counter",
    },
    {
        ...presetDefaults,
        id: 22,
        name: "Dine in",
        identification: "none",
        service_at: "table",
    },
    {
        ...presetDefaults,
        id: 23,
        name: "Takeaway",
        identification: "name",
        service_at: "counter",
        use_timing: true,
        slots_per_interval: 5,
        interval_time: 20,
    },
    {
        ...presetDefaults,
        id: 24,
        name: "Delivery",
        identification: "address",
        service_at: "delivery",
    },
];
