import { patch } from "@web/core/utils/patch";
import { PosPaymentMethod } from "@point_of_sale/../tests/unit/data/pos_payment_method.data";

patch(PosPaymentMethod.prototype, {
    _load_pos_self_data_read(records) {
        return [
            ...super._load_pos_self_data_read(records),
            ...records.filter((record) => record.type === "online"),
        ];
    },
});

PosPaymentMethod._records = [
    ...PosPaymentMethod._records,
    {
        id: 99,
        name: "Online payment",
        type: "online",
        image: false,
        sequence: 1,
        payment_method_type: "none",
        payment_provider: false,
        default_qr: false,
    },
];
