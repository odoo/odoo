import { patch } from "@web/core/utils/patch";
import { PosPayment } from "@point_of_sale/../tests/unit/data/pos_payment.data";

patch(PosPayment.prototype, {
    _load_pos_data_fields() {
        return [...super._load_pos_data_fields(), "viva_com_session_id"];
    },
});
