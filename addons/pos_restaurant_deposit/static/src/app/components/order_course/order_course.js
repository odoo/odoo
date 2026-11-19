import { sortDepositLines } from "@pos_deposit/app/utils/sort_deposit_lines";
import { patch } from "@web/core/utils/patch";
import { OrderCourse } from "@pos_restaurant/app/components/order_course/order_course";

patch(OrderCourse.prototype, {
    get comboSortedLines() {
        return sortDepositLines(super.comboSortedLines);
    },
});
