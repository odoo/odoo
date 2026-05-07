import { patch } from "@web/core/utils/patch";
import { PosPaymentMethod } from "@point_of_sale/../tests/unit/data/pos_payment_method.data";

patch(PosPaymentMethod.prototype, {
    _load_pos_data_fields() {
        return [...super._load_pos_data_fields(), "six_terminal_ip"];
    },
});

const baseSix = {
    is_cash_count: false,
    split_transactions: false,
    type: "bank",
    image: false,
    payment_method_type: "terminal",
    payment_provider: "six",
    default_qr: false,
};

PosPaymentMethod._records = [
    ...PosPaymentMethod._records,
    {
        ...baseSix,
        id: 100,
        name: "SIX (port 8080)",
        sequence: 10,
        six_terminal_ip: "10.0.0.1:8080",
    },
    {
        ...baseSix,
        id: 101,
        name: "SIX (default port)",
        sequence: 11,
        six_terminal_ip: "10.0.0.2",
    },
    {
        ...baseSix,
        id: 102,
        name: "SIX (shared IP)",
        sequence: 12,
        six_terminal_ip: "10.0.0.1:8080",
    },
];
