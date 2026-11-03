import { patch } from "@web/core/utils/patch";
import { hootPosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { models } from "@web/../tests/web_test_helpers";

export class EventTag extends models.ServerModel {
    _name = "event.tag";

    _load_pos_data_fields() {
        return ["id", "name", "color"];
    }

    _records = [
        {
            id: 1,
            name: "Tech",
        },
    ];
}

patch(hootPosModels, [...hootPosModels, EventTag]);
