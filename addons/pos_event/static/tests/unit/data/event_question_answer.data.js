import { patch } from "@web/core/utils/patch";
import { hootPosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { models } from "@web/../tests/web_test_helpers";

export class EventQuestionAnswer extends models.ServerModel {
    _name = "event.question.answer";

    _load_pos_data_fields() {
        return ["question_id", "name", "sequence"];
    }

    _records = [
        {
            id: 1,
            question_id: 4,
            name: "Male",
            sequence: 1,
        },
        {
            id: 2,
            question_id: 4,
            name: "Female",
            sequence: 2,
        },
    ];
}

patch(hootPosModels, [...hootPosModels, EventQuestionAnswer]);
