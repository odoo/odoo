import { patch } from "@web/core/utils/patch";
import { OrderCourse } from "@pos_restaurant/app/components/order_course/order_course";

patch(OrderCourse.prototype, {
    get comboSortedLines() {
        const regularLines = [];
        const serviceFeeLines = [];

        for (const line of this.course.lines) {
            (line.isServiceFeeLine() ? serviceFeeLines : regularLines).push(line);
        }

        const comboLines = [...regularLines, ...serviceFeeLines].reduce((acc, line) => {
            if (line.combo_line_ids?.length > 0) {
                acc.push(line, ...line.combo_line_ids);
            } else if (!line.combo_parent_id) {
                acc.push(line);
            }
            return acc;
        }, []);

        return this.course.order_id.sortDepositLines(comboLines);
    },
});
