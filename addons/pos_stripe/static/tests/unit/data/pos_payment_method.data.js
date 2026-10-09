import { patch } from "@web/core/utils/patch";
import { PosPaymentMethod } from "@point_of_sale/../tests/unit/data/pos_payment_method.data";

patch(PosPaymentMethod.prototype, {
    _load_pos_data_fields() {
        return [...super._load_pos_data_fields(), "stripe_serial_number"];
    },
});

PosPaymentMethod._records = [
    ...PosPaymentMethod._records,
    {
        id: 5,
        name: "Stripe",
        is_cash_count: false,
        split_transactions: false,
        type: "bank",
        image: false,
        sequence: 1,
        payment_method_type: "terminal",
        use_payment_terminal: "stripe",
        stripe_serial_number: "SIMULATOR",
        default_qr: false,
    },
];
