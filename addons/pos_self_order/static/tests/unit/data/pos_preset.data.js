import { patch } from "@web/core/utils/patch";
import { PosPreset } from "@point_of_sale/../tests/unit/data/pos_preset.data";

patch(PosPreset.prototype, {
    _load_pos_data_fields() {
        return [...super._load_pos_data_fields(), "mail_template_id"];
    },
});
