import { PosConfig } from "@point_of_sale/../tests/unit/data/pos_config.data";

PosConfig._records = PosConfig._records.map((record) => ({
    ...record,
    use_fast_payment: true,
    payment_method_ids: [...record.payment_method_ids, 101],
    fast_payment_method_ids: [...record.fast_payment_method_ids, 101],
}));
