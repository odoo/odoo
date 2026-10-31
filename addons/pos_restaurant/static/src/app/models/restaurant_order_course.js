import { registry } from "@web/core/registry";
import { Base } from "@point_of_sale/app/models/related_models";

const { DateTime, Interval } = luxon;

export class RestaurantOrderCourse extends Base {
    static pythonModel = "restaurant.order.course";

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

    get isLive() {
        return this.fired_date && this.id === this.order_id.getFiredCourses.at(-1)[0];
    }

    getDuration() {
        if (!this.fired_date) {
            return false;
        }

        const firedCourses = this.order_id.getFiredCourses;
        const index = firedCourses.findIndex(([id]) => id === this.id);
        if (index === -1) {
            return false;
        }

        const start = firedCourses[index][1];
        const end = firedCourses[index + 1]?.[1] ?? DateTime.now();
        const duration = Interval.fromDateTimes(start, end).toDuration(["hours", "minutes"]);
        if (!duration.isValid || (!duration.hours && !duration.minutes) || duration.minutes < 1) {
            return false;
        }
        return duration.hours ? duration.toFormat("h'h'm''") : duration.toFormat("m''");
    }
}

registry
    .category("pos_available_models")
    .add(RestaurantOrderCourse.pythonModel, RestaurantOrderCourse);
