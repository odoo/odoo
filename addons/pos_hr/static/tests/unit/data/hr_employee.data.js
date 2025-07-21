import { patch } from "@web/core/utils/patch";
import { hootPosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { models } from "@web/../tests/web_test_helpers";

export class HrEmployee extends models.ServerModel {
    _name = "hr.employee";

    _load_pos_data_fields() {
        return ["name", "user_id", "work_contact_id"];
    }
}

patch(hootPosModels, [...hootPosModels, HrEmployee]);
