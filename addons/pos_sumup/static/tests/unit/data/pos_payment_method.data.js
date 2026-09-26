import { PosPaymentMethod } from "@point_of_sale/../tests/unit/data/pos_payment_method.data";

PosPaymentMethod._records = [
    ...PosPaymentMethod._records,
    {
        id: 4,
        name: "SumUp",
        type: "bank",
        image: false,
        sequence: 1,
        payment_method_type: "terminal",
        payment_provider: "sumup",
        default_qr: false,
        currency_ids: [1],
        write_date: "2025-01-01 10:00:00",
    },
];
