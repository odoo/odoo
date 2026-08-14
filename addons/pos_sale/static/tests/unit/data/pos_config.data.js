import { PosConfig } from "@point_of_sale/../tests/unit/data/pos_config.data";

PosConfig._records = PosConfig._records.map((config) => {
    if (config.id === 1) {
        return {
            ...config,
            down_payment_product_id: 105,
            default_product_id: 106,
            sale_order_payment_method_id: 21,
        };
    }
    return config;
});
