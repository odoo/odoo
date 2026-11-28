import { patch } from "@web/core/utils/patch";
import { PosConfig } from "@point_of_sale/../tests/unit/data/pos_config.data";

patch(PosConfig.prototype, {
    _load_pos_data_read(data) {
        data = super._load_pos_data_read(...arguments);
        // mirrors sale.order._get_pos_payable_domain(config)
        data[0]["_sale_order_payable_domain"] = [
            "&",
            "&",
            "&",
            ["state", "!=", "cancel"],
            ["invoice_status", "!=", "invoiced"],
            ["currency_id", "=", data[0].currency_id],
            "|",
            "|",
            ["amount_unpaid", ">", 0],
            ["amount_total", "<=", 0],
            ["order_line.is_downpayment", "=", true],
        ];
        return data;
    },
});

PosConfig._records = PosConfig._records.map((config) => {
    if (config.id === 1) {
        return {
            ...config,
            down_payment_product_id: 105,
            default_product_id: 106,
        };
    }
    return config;
});
