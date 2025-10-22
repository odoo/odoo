import { patch } from "@web/core/utils/patch";
import { hootPosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { models } from "@web/../tests/web_test_helpers";

export class RestaurantTable extends models.ServerModel {
    _name = "restaurant.table";

    _load_pos_data_fields() {
        return [
            "table_number",
            "width",
            "height",
            "position_h",
            "position_v",
            "parent_id",
            "shape",
            "floor_id",
            "color",
            "seats",
            "active",
        ];
    }

    _records = [
        {
            id: 2,
            table_number: 1,
            width: 90,
            height: 90,
            position_h: 407,
            position_v: 88,
            parent_id: false,
            shape: "square",
            floor_id: 2,
            color: "rgb(53,211,116)",
            seats: 4,
            active: true,
        },
        {
            id: 3,
            table_number: 2,
            width: 90,
            height: 90,
            position_h: 732,
            position_v: 221,
            parent_id: false,
            shape: "square",
            floor_id: 2,
            color: "rgb(53,211,116)",
            seats: 4,
            active: true,
        },
        {
            id: 4,
            table_number: 4,
            width: 165,
            height: 100,
            position_h: 762,
            position_v: 83,
            parent_id: false,
            shape: "square",
            floor_id: 2,
            color: "rgb(53,211,116)",
            seats: 4,
            active: true,
        },
        {
            id: 14,
            table_number: 101,
            width: 130,
            height: 85,
            position_h: 100,
            position_v: 50,
            parent_id: false,
            shape: "square",
            floor_id: 3,
            color: "rgb(53,211,116)",
            seats: 2,
            active: true,
        },
        {
            id: 15,
            table_number: 102,
            width: 130,
            height: 85,
            position_h: 100,
            position_v: 166,
            parent_id: false,
            shape: "square",
            floor_id: 3,
            color: "rgb(53,211,116)",
            seats: 2,
            active: true,
        },
        {
            id: 16,
            table_number: 103,
            width: 130,
            height: 85,
            position_h: 100,
            position_v: 283,
            parent_id: false,
            shape: "square",
            floor_id: 3,
            color: "rgb(53,211,116)",
            seats: 2,
            active: true,
        },
    ];
}

patch(hootPosModels, [...hootPosModels, RestaurantTable]);
