import { PosPaymentMethod } from "@point_of_sale/../tests/unit/data/pos_payment_method.data";

PosPaymentMethod._records = [
    ...PosPaymentMethod._records,
    {
        id: 101,
        name: "QR Code",
        is_cash_count: false,
        split_transactions: false,
        type: "bank",
        image: false,
        sequence: 1,
        payment_method_type: "qr_code",
        default_qr: false,
        is_online_payment: false,
    },
];
