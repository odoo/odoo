import { patch } from "@web/core/utils/patch";
import { PosPaymentMethod } from "@point_of_sale/../tests/unit/data/pos_payment_method.data";

patch(PosPaymentMethod.prototype, {
    _load_pos_data_fields() {
        return [...super._load_pos_data_fields(), "viva_com_terminal_id"];
    },
});

PosPaymentMethod._records = [
    ...PosPaymentMethod._records,
    {
        id: 6,
        name: "Viva",
        is_cash_count: false,
        split_transactions: false,
        type: "bank",
        image: false,
        sequence: 1,
        payment_method_type: "terminal",
        use_payment_terminal: "viva_com",
        viva_com_terminal_id: "01234543210",
        default_qr: false,
    },
];
