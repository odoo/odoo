import { patch } from "@web/core/utils/patch";
import {
    modelsToLoad,
    posModels,
    PosOrderLine,
    PosPreset,
} from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { defineModels, models } from "@web/../tests/web_test_helpers";

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
}

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
}

export class RestaurantOrderCourse extends models.ServerModel {
    _name = "restaurant.order.course";

    _load_pos_data_fields() {
        return ["uuid", "fired", "order_id", "line_ids", "index", "write_date"];
    }
}

patch(PosOrderLine.prototype, {
    _load_pos_data_fields() {
        return [...super._load_pos_data_fields(), "course_id"];
    },
});

patch(PosPreset.prototype, {
    _load_pos_data_fields() {
        return [...super._load_pos_data_fields(), "use_guest"];
    },
});

patch(modelsToLoad, [
    ...modelsToLoad,
    "restaurant.floor",
    "restaurant.table",
    "restaurant.order.course",
]);
patch(posModels, [...posModels, RestaurantFloor, RestaurantTable, RestaurantOrderCourse]);
defineModels([RestaurantFloor, RestaurantTable, RestaurantOrderCourse]);
