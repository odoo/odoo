import { PosConfig } from "@point_of_sale/../tests/unit/data/pos_config.data";

PosConfig._records = PosConfig._records.map((record) => ({
    ...record,
    picking_type_id: 9,
    ship_later: false,
    warehouse_id: false,
    route_id: false,
    picking_policy: "direct",
}));
