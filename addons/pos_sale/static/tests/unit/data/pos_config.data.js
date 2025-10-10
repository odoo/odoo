import { PosConfig } from "@point_of_sale/../tests/unit/data/pos_config.data";

PosConfig._records = PosConfig._records.map((config) => {
    if (config.id === 1) {
        return {
            ...config,
            down_payment_product_id: 15,
        };
    }
    return config;
});
