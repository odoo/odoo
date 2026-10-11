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
