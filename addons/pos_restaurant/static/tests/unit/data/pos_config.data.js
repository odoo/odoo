import { PosConfig } from "@point_of_sale/../tests/unit/data/pos_config.data";

PosConfig._records = PosConfig._records.map((record) => ({
    ...record,
    module_pos_restaurant: true,
    floor_ids: [2, 3],
    iface_tipproduct: true,
    tip_product_id: 1,
    set_tip_after_payment: true,
    default_screen: "tables",
}));
