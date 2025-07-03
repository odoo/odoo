import { patch } from "@web/core/utils/patch";
import { hootPosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { models } from "@web/../tests/web_test_helpers";

export class EventQuestion extends models.ServerModel {
    _name = "event.question";

    _load_pos_data_fields() {
        return [
            "title",
            "question_type",
            "event_type_id",
            "event_id",
            "sequence",
            "once_per_order",
            "is_mandatory_answer",
            "answer_ids",
        ];
    }
}

patch(hootPosModels, [...hootPosModels, EventQuestion]);
