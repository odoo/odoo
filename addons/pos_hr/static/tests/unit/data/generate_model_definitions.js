import { patch } from "@web/core/utils/patch";
import {
    modelsToLoad,
    posModels,
    PosPayment,
} from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { defineModels, models } from "@web/../tests/web_test_helpers";

export class HrEmployee extends models.ServerModel {
    _name = "hr.employee";

    _load_pos_data_fields() {
        return ["name", "user_id", "work_contact_id"];
    }
}

patch(PosPayment.prototype, {
    _load_pos_data_fields() {
        return [...super._load_pos_data_fields(), "employee_id"];
    },
});

patch(modelsToLoad, [...modelsToLoad, "hr.employee"]);
patch(posModels, [...posModels, HrEmployee]);
defineModels([HrEmployee]);
