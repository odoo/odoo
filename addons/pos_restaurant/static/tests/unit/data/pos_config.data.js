import { PosConfig } from "@point_of_sale/../tests/unit/data/pos_config.data";

PosConfig._records = PosConfig._records.map((record) => ({
    ...record,
    module_pos_restaurant: true,
    floor_ids: [2, 3],
}));
