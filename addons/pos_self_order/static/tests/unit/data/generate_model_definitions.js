import { patch } from "@web/core/utils/patch";
import {
    ProductTemplate,
    PosPreset,
} from "@point_of_sale/../tests/unit/data/generate_model_definitions";

patch(ProductTemplate.prototype, {
    _load_pos_data_fields() {
        return [...super._load_pos_data_fields(), "self_order_available"];
    },
});

patch(PosPreset.prototype, {
    _load_pos_data_fields() {
        return [...super._load_pos_data_fields(), "mail_template_id"];
    },
});
