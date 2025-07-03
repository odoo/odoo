import { patch } from "@web/core/utils/patch";
import { hootPosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { models } from "@web/../tests/web_test_helpers";

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

patch(hootPosModels, [...hootPosModels, EventEventTicket]);
