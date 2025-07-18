import { patch } from "@web/core/utils/patch";
import { PosConfig } from "@point_of_sale/../tests/unit/data/pos_config.data";

patch(PosConfig.prototype, {
    _load_pos_self_data_read(records) {
        records[0]._pos_special_products_ids = [1]; // TIPS product
        records[0]._self_ordering_image_background_ids = [];
        records[0]._self_ordering_image_home_ids = [];
        return records;
    },
});

PosConfig._records = PosConfig._records.map((record) => ({
    ...record,
    self_ordering_mode: "kiosk",
}));
