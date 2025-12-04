import { patch } from "@web/core/utils/patch";
import { hootPosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { models } from "@web/../tests/web_test_helpers";

export class RestaurantTable extends models.ServerModel {
    _name = "restaurant.table";

    _load_pos_data_fields() {
        return ["table_number", "floor_id", "seats", "parent_id", "active"];
    }

    _records = [
        {
            id: 2,
            table_number: 1,
            parent_id: false,
            parent_side: false,
            floor_id: 2,
            seats: 4,
            active: true,
            floor_plan_layout: {
                width: 90,
                height: 90,
                left: 407,
                top: 88,
                shape: "square",
                color: "rgb(53,211,116)",
            },
        },
        {
            id: 3,
            table_number: 2,
            parent_id: false,
            parent_side: false,
            floor_id: 2,
            seats: 4,
            active: true,
            floor_plan_layout: {
                width: 90,
                height: 90,
                left: 732,
                top: 221,
                shape: "square",
                color: "rgb(53,211,116)",
            },
        },
        {
            id: 4,
            table_number: 4,
            parent_id: false,
            parent_side: false,
            floor_id: 2,
            seats: 4,
            active: true,
            floor_plan_layout: {
                width: 165,
                height: 100,
                left: 762,
                top: 83,
                shape: "square",
                color: "rgb(53,211,116)",
            },
        },
        {
            id: 14,
            table_number: 101,
            parent_id: false,
            parent_side: false,
            floor_id: 3,
            seats: 2,
            active: true,
            floor_plan_layout: {
                width: 130,
                height: 85,
                left: 762,
                top: 83,
                shape: "square",
                color: "rgb(53,211,116)",
            },
        },
        {
            id: 15,
            table_number: 102,
            parent_id: false,
            parent_side: false,
            floor_id: 3,
            seats: 2,
            active: true,
            floor_plan_layout: {
                width: 130,
                height: 85,
                left: 100,
                top: 166,
                shape: "square",
                color: "rgb(53,211,116)",
            },
        },
        {
            id: 16,
            table_number: 103,
            parent_id: false,
            parent_side: false,
            floor_id: 3,
            seats: 2,
            active: true,
            floor_plan_layout: {
                width: 130,
                height: 85,
                left: 100,
                top: 283,
                shape: "square",
                color: "rgb(53,211,116)",
            },
        },
    ];
}

patch(hootPosModels, [...hootPosModels, RestaurantTable]);
