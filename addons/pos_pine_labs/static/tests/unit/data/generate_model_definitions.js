import { patch } from "@web/core/utils/patch";
import { PosPayment } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

patch(PosPayment.prototype, {
    _load_pos_data_fields() {
        return [...super._load_pos_data_fields(), "pine_labs_plutus_transaction_ref"];
    },
});
