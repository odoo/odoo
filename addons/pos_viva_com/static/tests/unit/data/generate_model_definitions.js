import { patch } from "@web/core/utils/patch";
import {
    PosPayment,
    PosPaymentMethod,
} from "@point_of_sale/../tests/unit/data/generate_model_definitions";

patch(PosPayment.prototype, {
    _load_pos_data_fields() {
        return [...super._load_pos_data_fields(), "viva_com_session_id"];
    },
});

patch(PosPaymentMethod.prototype, {
    _load_pos_data_fields() {
        return [...super._load_pos_data_fields(), "viva_com_terminal_id"];
    },
});
