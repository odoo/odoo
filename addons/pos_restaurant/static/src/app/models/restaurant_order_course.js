import { registry } from "@web/core/registry";
import { Base } from "@point_of_sale/app/models/related_models";
import { _t } from "@web/core/l10n/translation";

export class RestaurantOrderCourse extends Base {
    static pythonModel = "restaurant.order.course";

    get name() {
        return _t("Course") + " " + this.index;
    }
    isSelected() {
        return this.order_id?.uiState.selected_course_uuid === this.uuid;
    }
    get lines() {
        return this.line_ids;
    }
    isEmpty() {
        return this.line_ids?.length === 0;
    }
    isReadyToFire() {
        return !this.fired && !this.isEmpty();
    }
}

registry
    .category("pos_available_models")
    .add(RestaurantOrderCourse.pythonModel, RestaurantOrderCourse);
