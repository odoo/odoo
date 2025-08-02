import { patch } from "@web/core/utils/patch";
import { hootPosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { models } from "@web/../tests/web_test_helpers";

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

    _records = [
        {
            id: 1,
            date: "2019-03-11",
            display_name: "Event Slot 1",
            event_id: 1,
            registration_ids: [],
            seats_available: 5,
            start_datetime: "2019-03-11 11:00:00",
        },
    ];
}

patch(hootPosModels, [...hootPosModels, EventSlot]);
