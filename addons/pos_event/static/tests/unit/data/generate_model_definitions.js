import { patch } from "@web/core/utils/patch";
import {
    modelsToLoad,
    posModels,
    PosOrderLine,
} from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { defineModels, models } from "@web/../tests/web_test_helpers";

export class EventEventTicket extends models.ServerModel {
    _name = "event.event.ticket";

    _load_pos_data_fields() {
        return [
            "id",
            "name",
            "event_id",
            "seats_used",
            "seats_available",
            "price",
            "product_id",
            "seats_max",
            "start_sale_datetime",
            "end_sale_datetime",
        ];
    }
}

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

export class EventSlot extends models.ServerModel {
    _name = "event.slot";

    _load_pos_data_fields() {
        return [
            "id",
            "date",
            "display_name",
            "event_id",
            "registration_ids",
            "seats_available",
            "start_datetime",
        ];
    }
}

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

export class EventQuestionAnswer extends models.ServerModel {
    _name = "event.question.answer";

    _load_pos_data_fields() {
        return ["question_id", "name", "sequence"];
    }
}

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

patch(PosOrderLine.prototype, {
    _load_pos_data_fields() {
        return [...super._load_pos_data_fields(), "event_ticket_id", "event_registration_ids"];
    },
});

patch(modelsToLoad, [
    ...modelsToLoad,
    "event.event.ticket",
    "event.event",
    "event.slot",
    "event.registration",
    "event.question",
    "event.question.answer",
    "event.registration.answer",
]);
patch(posModels, [
    ...posModels,
    EventEventTicket,
    EventEvent,
    EventSlot,
    EventRegistration,
    EventQuestion,
    EventQuestionAnswer,
    EventRegistrationAnswer,
]);
defineModels([
    EventEventTicket,
    EventEvent,
    EventSlot,
    EventRegistration,
    EventQuestion,
    EventQuestionAnswer,
    EventRegistrationAnswer,
]);
