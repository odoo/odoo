import { patch } from "@web/core/utils/patch";
import { hootPosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { models } from "@web/../tests/web_test_helpers";

export class EventQuestion extends models.ServerModel {
    _name = "event.question";

    _load_pos_data_fields() {
        return [
            "title",
            "question_type",
            "event_type_ids",
            "event_ids",
            "sequence",
            "once_per_order",
            "is_mandatory_answer",
            "answer_ids",
        ];
    }

    _records = [
        {
            id: 1,
            title: "Name",
            question_type: "name",
            event_ids: [1],
            sequence: 1,
            once_per_order: false,
            is_mandatory_answer: true,
            answer_ids: [],
        },
        {
            id: 2,
            title: "Email",
            question_type: "email",
            event_ids: [1],
            sequence: 2,
            once_per_order: false,
            is_mandatory_answer: true,
            answer_ids: [],
        },
        {
            id: 3,
            title: "Phone",
            question_type: "phone",
            event_ids: [1],
            sequence: 3,
            once_per_order: false,
            is_mandatory_answer: true,
            answer_ids: [],
        },
        {
            id: 4,
            title: "Gender",
            question_type: "simple_choice",
            event_ids: [1],
            sequence: 4,
            once_per_order: false,
            is_mandatory_answer: false,
            answer_ids: [1, 2],
        },
    ];
}

patch(hootPosModels, [...hootPosModels, EventQuestion]);
