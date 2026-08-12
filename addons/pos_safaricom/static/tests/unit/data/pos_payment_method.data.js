import { patch } from "@web/core/utils/patch";
import { PosPaymentMethod } from "@point_of_sale/../tests/unit/data/pos_payment_method.data";

patch(PosPaymentMethod.prototype, {
    _load_pos_data_fields() {
        return [...super._load_pos_data_fields(), "safaricom_payment_type"];
    },
});

PosPaymentMethod._records = [
    ...PosPaymentMethod._records,
    {
        id: 7,
        name: "M-PESA Express",
        payment_provider: "safaricom",
        type: "bank",
        image: false,
        sequence: 3,
        payment_method_type: "none",
        default_qr: false,
        safaricom_payment_type: "mpesa_express",
    },
    {
        id: 8,
        name: "Lipa na M-PESA",
        payment_provider: "safaricom",
        type: "bank",
        image: false,
        sequence: 4,
        payment_method_type: "none",
        default_qr: false,
        safaricom_payment_type: "lipa_na_mpesa",
    },
];
