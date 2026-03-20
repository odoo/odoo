import { patch } from "@web/core/utils/patch";
import { PosCategory } from "@point_of_sale/../tests/unit/data/pos_category.data";

patch(PosCategory.prototype, {
    _load_pos_data_fields() {
        return [...super._load_pos_data_fields(), "course_id"];
    },
});
