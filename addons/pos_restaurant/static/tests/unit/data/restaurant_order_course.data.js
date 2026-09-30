import { patch } from "@web/core/utils/patch";
import { hootPosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { models } from "@web/../tests/web_test_helpers";

export class RestaurantOrderCourse extends models.ServerModel {
    _name = "restaurant.order.course";

    _load_pos_data_fields() {
        return ["uuid", "fired", "order_id", "line_ids", "index", "write_date"];
    }
}

patch(hootPosModels, [...hootPosModels, RestaurantOrderCourse]);
