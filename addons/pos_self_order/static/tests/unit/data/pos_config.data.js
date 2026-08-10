import { patch } from "@web/core/utils/patch";
import { PosConfig } from "@point_of_sale/../tests/unit/data/pos_config.data";

patch(PosConfig.prototype, {
    _load_pos_self_data_read(records) {
        records[0]._pos_special_products_ids = [1, 211, 212]; // TIPS product
        records[0]._self_ordering_image_home_ids = [
            { id: 100, mimetype: "image/jpeg" },
            { id: 101, mimetype: "image/jpeg" },
            { id: 102, mimetype: "image/jpeg" },
        ];
        records[0]._self_ordering_image_background_ids = [103];
        records[0]._base_url = "http://localhost:4444";
        return records;
    },
});

PosConfig._records = PosConfig._records.map((record) => ({
    ...record,
    self_ordering_mode: "kiosk",
    self_ordering_pay_after: "each",
    self_ordering_service_mode: "counter",
    module_pos_restaurant: true,
    available_preset_ids: [1, 2, 20, 21, 22, 23, 24],
    default_preset_id: 20,
    use_presets: true,
}));
