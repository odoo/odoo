import { PosPaymentMethod } from "@point_of_sale/../tests/unit/data/pos_payment_method.data";

PosPaymentMethod._records = [
    ...PosPaymentMethod._records,
    {
        id: 7,
        name: "Worldline",
        is_cash_count: false,
        split_transactions: false,
        type: "bank",
        image: false,
        sequence: 1,
        payment_method_type: "terminal",
        payment_provider: "worldline_api",
        default_qr: false,
    },
];
