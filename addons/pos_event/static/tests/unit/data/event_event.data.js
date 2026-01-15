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

    _records = [
        {
            id: 1,
            name: "Odoo Community Days",
            seats_available: 10,
            event_ticket_ids: [1],
            registration_ids: [],
            seats_limited: true,
            write_date: "2019-03-10 11:00:00",
            question_ids: [1, 2, 3, 4],
            general_question_ids: [],
            specific_question_ids: [],
            badge_format: "A6",
            seats_max: 10,
            is_multi_slots: true,
            event_slot_ids: [1],
        },
    ];

    get_slot_tickets_availability_pos(self, slot_ticket_ids) {
        return [5];
    }
}

patch(hootPosModels, [...hootPosModels, EventEvent]);
