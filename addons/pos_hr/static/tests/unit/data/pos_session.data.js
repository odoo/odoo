import { patch } from "@web/core/utils/patch";
import { PosSession } from "@point_of_sale/../tests/unit/data/pos_session.data";

patch(PosSession.prototype, {
    _load_pos_data_models() {
        return [...super._load_pos_data_models(), "hr.employee"];
    },
    _load_pos_data_fields() {
        return [...super._load_pos_data_fields(), "employee_id"];
    },
});
