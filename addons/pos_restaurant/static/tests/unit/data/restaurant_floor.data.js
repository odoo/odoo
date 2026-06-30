import { patch } from "@web/core/utils/patch";
import { hootPosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { models } from "@web/../tests/web_test_helpers";

export class RestaurantFloor extends models.ServerModel {
    _name = "restaurant.floor";

    _load_pos_data_fields() {
        return [
            "name",
            "background_color",
            "table_ids",
            "sequence",
            "pos_config_ids",
            "floor_background_image",
        ];
    }

    _records = [
        {
            id: 2,
            name: "Main Floor",
            background_color: "red",
            table_ids: [2, 3, 4],
            sequence: 1,
            pos_config_ids: [1],
            floor_background_image: false,
        },
        {
            id: 3,
            name: "Patio",
            background_color: "rgb(130, 233, 171)",
            table_ids: [14, 15, 16],
            sequence: 1,
            pos_config_ids: [1],
            floor_background_image: false,
        },
    ];
}

patch(hootPosModels, [...hootPosModels, RestaurantFloor]);
