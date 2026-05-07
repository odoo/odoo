import { PosConfig } from "@point_of_sale/../tests/unit/data/pos_config.data";

PosConfig._records = PosConfig._records.map((record) => ({
    ...record,
    payment_method_ids: [...(record.payment_method_ids || []), 100, 101, 102],
}));
