import { patch } from "@web/core/utils/patch";
import { hootPosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { models } from "@web/../tests/web_test_helpers";

export class EventEvent extends models.ServerModel {
    _name = "event.event";

    _load_pos_data_fields() {
        return [
            "id",
            "name",
            "seats_available",
            "event_ticket_ids",
            "registration_ids",
            "seats_limited",
            "write_date",
            "question_ids",
            "general_question_ids",
            "specific_question_ids",
            "badge_format",
            "seats_max",
            "is_multi_slots",
            "event_slot_ids",
        ];
    }
}

patch(hootPosModels, [...hootPosModels, EventEvent]);
