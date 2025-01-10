import { registry } from "@web/core/registry";
import { Base } from "@point_of_sale/app/models/related_models";
import { _t } from "@web/core/l10n/translation";

export class RestaurantOrderCourse extends Base {
    static pythonModel = "restaurant.order.course";

    setup(vals) {
        super.setup(vals);
        this.uiState = {};
    }
    serialize(options = {}) {
        const data = super.serialize(...arguments);
        if (options.orm === true) {
            // The line_ids relationship is serialized in pos_order (restaurant_course_lines)
            // using a course_uuid -> line_uuids mapping to prevent inserting the same new line
            // multiple times in the data model.
            delete data.line_ids;
        }
        return data;
    }
    get name() {
        return _t("Course") + " " + this.index;
    }
    isSelected() {
        return this.order_id.uiState.selected_course_uuid === this.uuid;
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
    isNew() {
        return typeof this.id === "string";
    }
}

registry
    .category("pos_available_models")
    .add(RestaurantOrderCourse.pythonModel, RestaurantOrderCourse);
