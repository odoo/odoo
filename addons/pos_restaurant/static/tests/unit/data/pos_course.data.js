import { patch } from "@web/core/utils/patch";
import { hootPosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { models } from "@web/../tests/web_test_helpers";

export class PosCourse extends models.ServerModel {
    _name = "pos.course";

    _load_pos_data_fields() {
        return ["name", "sequence", "category_ids"];
    }

    _records = [
        { id: 1, name: "Default Course 1", sequence: 1, category_ids: [1] },
        { id: 2, name: "Default Course 2", sequence: 2, category_ids: [2] },
    ];
}

patch(hootPosModels, [...hootPosModels, PosCourse]);
