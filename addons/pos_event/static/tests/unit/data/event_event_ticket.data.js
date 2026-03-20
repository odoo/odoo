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

    _records = [
        {
            id: 1,
            name: "Standard",
            event_id: 1,
            seats_used: 0,
            seats_available: 5,
            price: 100,
            product_id: 106,
            seats_max: 5,
            start_sale_datetime: "2019-03-10 11:00:00",
            end_sale_datetime: "2019-03-15 12:00:00",
        },
        {
            id: 2,
            name: "Unlimited Ticket",
            event_id: false,
            seats_used: 0,
            seats_available: 0,
            price: 100,
            product_id: 106,
            seats_max: 0,
            start_sale_datetime: "2019-03-10 11:00:00",
            end_sale_datetime: "2019-03-15 12:00:00",
        },
        {
            id: 5,
            name: "Limited Ticket",
            event_id: 5,
            seats_used: 0,
            seats_available: 3,
            price: 100,
            product_id: 106,
            seats_max: 5,
            start_sale_datetime: "2019-03-10 11:00:00",
            end_sale_datetime: "2019-03-15 12:00:00",
        },
    ];
}

patch(hootPosModels, [...hootPosModels, EventEventTicket]);
