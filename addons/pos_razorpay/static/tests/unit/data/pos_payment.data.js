import { patch } from "@web/core/utils/patch";
import { PosPayment } from "@point_of_sale/../tests/unit/data/pos_payment.data";

patch(PosPayment.prototype, {
    _load_pos_data_fields() {
        return [
            ...super._load_pos_data_fields(),
            "razorpay_reverse_ref_no",
            "razorpay_p2p_request_id",
        ];
    },
});
