import { patch } from "@web/core/utils/patch";
import { hootPosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { models } from "@web/../tests/web_test_helpers";

export class EventQuestionAnswer extends models.ServerModel {
    _name = "event.question.answer";

    _load_pos_data_fields() {
        return ["question_id", "name", "sequence"];
    }
}

patch(hootPosModels, [...hootPosModels, EventQuestionAnswer]);
