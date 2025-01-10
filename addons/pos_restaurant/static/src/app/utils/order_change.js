import { receiptLineGrouper } from "@point_of_sale/app/models/utils/order_change";
import { patch } from "@web/core/utils/patch";

patch(receiptLineGrouper, {
    getGroup(line) {
        if (!line.config?.module_pos_restaurant || !line.course_id) {
            return super.getGroup(line);
        }
        return { index: line.course_id.index, name: line.course_id.name };
    },
});
