import { LoyaltyReward } from "@pos_loyalty/app/models/loyalty_reward";
import { patch } from "@web/core/utils/patch";

patch(LoyaltyReward.prototype, {
    getRewardLines(order, points, opts) {
        const lineValues = super.getRewardLines(order, points, opts);
        // Assign the order's last course to the reward lines.
        if (order.hasCourses()) {
            const course = order.getLastCourse();
            lineValues.forEach((line) => {
                line.course_id = course;
            });
        }
        return lineValues;
    },
});
