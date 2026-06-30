import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    _getRewardLineValues(args) {
        const lineValues = super._getRewardLineValues(args);
        // Assign last course to reward lines
        if (this.hasCourses()) {
            const course = this.getLastCourse();
            lineValues.forEach((line) => {
                line.course_id = course;
            });
        }
        return lineValues;
    },
});
