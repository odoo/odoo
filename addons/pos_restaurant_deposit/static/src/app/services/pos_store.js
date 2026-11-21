import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

patch(PosStore.prototype, {
    async addLineToOrder(vals, order, opts = {}, configure = true) {
        const line = await super.addLineToOrder(vals, order, opts, configure);
        if (line && !vals.deposit_main_line_id) {
            line.syncCourseWithRelatedLines();
        }
        return line;
    },

    async mergeOrders(sourceOrder, destOrder) {
        for (const depositLine of sourceOrder.lines.filter((line) => line.deposit_main_line_id)) {
            if (
                destOrder.lines.some((line) =>
                    line.canBeMergedWith(depositLine.deposit_main_line_id)
                )
            ) {
                depositLine.delete();
            }
        }
        return super.mergeOrders(...arguments);
    },
});
