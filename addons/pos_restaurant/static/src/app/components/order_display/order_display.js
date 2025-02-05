import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { OrderDisplay } from "@point_of_sale/app/components/order_display/order_display";
import { OrderCourse } from "@pos_restaurant/app/components/order_course/order_course";
patch(OrderDisplay.prototype, {
    emptyCartText() {
        let text = super.emptyCartText(...arguments);
        if (this.order.config.module_pos_restaurant && !this.order.isBooked) {
            text += " " + _t("or book the table for later");
        }
        return text;
    },

    get displayCourses() {
        if (
            !this.order.config.module_pos_restaurant ||
            this.props.mode !== "display" ||
            this.order.finalized
        ) {
            return false;
        }
        return this.order.course_ids.length > 0;
    },
});
OrderDisplay.components = { ...OrderDisplay.components, OrderCourse };
