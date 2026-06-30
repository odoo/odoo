import { patch } from "@web/core/utils/patch";
import { hootPosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { models } from "@web/../tests/web_test_helpers";
import { isIterable } from "@web/core/utils/arrays";

const { DateTime } = luxon;

export class RestaurantOrderCourse extends models.ServerModel {
    _name = "restaurant.order.course";

    create() {
        const restaurantOrderCourse = super.create(...arguments);
        this.write(
            isIterable(restaurantOrderCourse) ? restaurantOrderCourse : [restaurantOrderCourse.id],
            {
                write_date: DateTime.now().toFormat("yyyy-MM-dd HH:mm:ss"),
            }
        );
        return restaurantOrderCourse;
    }

    _load_pos_data_fields() {
        return [
            "name",
            "course_id",
            "uuid",
            "fired",
            "order_id",
            "line_ids",
            "index",
            "write_date",
        ];
    }
}

patch(hootPosModels, [...hootPosModels, RestaurantOrderCourse]);
