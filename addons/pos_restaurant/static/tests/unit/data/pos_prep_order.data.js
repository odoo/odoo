import { patch } from "@web/core/utils/patch";
import { PosPrepOrder } from "@point_of_sale/../tests/unit/data/pos_prep_order.data";

patch(PosPrepOrder.prototype, {
    fire_course(order_id, course_id) {
        //ToDo: no order_id/course_id it's uuids
    },
});
