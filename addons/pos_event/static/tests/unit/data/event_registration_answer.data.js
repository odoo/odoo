import { patch } from "@web/core/utils/patch";
import { hootPosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { models } from "@web/../tests/web_test_helpers";

export class EventRegistrationAnswer extends models.ServerModel {
    _name = "event.registration.answer";

    _load_pos_data_fields() {
        return [
            "question_id",
            "registration_id",
            "value_answer_id",
            "value_text_box",
            "partner_id",
            "write_date",
            "event_id",
        ];
    }
}

patch(hootPosModels, [...hootPosModels, EventRegistrationAnswer]);
