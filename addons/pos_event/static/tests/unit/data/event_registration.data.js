import { patch } from "@web/core/utils/patch";
import { hootPosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { models } from "@web/../tests/web_test_helpers";

export class EventRegistration extends models.ServerModel {
    _name = "event.registration";

    _load_pos_data_fields() {
        return [
            "id",
            "event_id",
            "event_ticket_id",
            "event_slot_id",
            "pos_order_line_id",
            "pos_order_id",
            "phone",
            "email",
            "name",
            "registration_answer_ids",
            "registration_answer_choice_ids",
            "write_date",
        ];
    }
}

patch(hootPosModels, [...hootPosModels, EventRegistration]);
