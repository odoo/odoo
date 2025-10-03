import { PosPaymentMethod } from "@point_of_sale/../tests/unit/data/pos_payment_method.data";
import { patch } from "@web/core/utils/patch";

patch(PosPaymentMethod.prototype, {
    _load_pos_self_data_read(records) {
        return records.filter((record) => record.use_payment_terminal);
    },
});
