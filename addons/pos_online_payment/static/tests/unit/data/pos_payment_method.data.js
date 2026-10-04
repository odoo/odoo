import { patch } from "@web/core/utils/patch";
import { PosPaymentMethod } from "@point_of_sale/../tests/unit/data/pos_payment_method.data";

export const ONLINE_PAYMENT_METHOD_ID = 99;

patch(PosPaymentMethod.prototype, {
    _load_pos_data_read(records) {
        const readRecords = super._load_pos_data_read?.(records) ?? records;
        for (const record of readRecords) {
            if (record.type === "online") {
                record._customer_required = false;
            }
        }
        return readRecords;
    },
});

PosPaymentMethod._records = [
    ...PosPaymentMethod._records,
    {
        id: ONLINE_PAYMENT_METHOD_ID,
        name: "Online payment",
        payment_provider: false,
        type: "online",
        image: false,
        sequence: 3,
        payment_method_type: "none",
        default_qr: false,
    },
];
