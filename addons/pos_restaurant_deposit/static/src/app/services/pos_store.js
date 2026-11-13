import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

patch(PosStore.prototype, {
    async addLineToOrder(vals, order, opts = {}, configure = true) {
        const line = await super.addLineToOrder(vals, order, opts, configure);

        if (!line || vals.deposit_main_line_id) {
            return line;
        }

        for (const mainLine of [line, ...line.combo_line_ids]) {
            const depositLine = mainLine.depositLine;

            if (depositLine) {
                depositLine.update({
                    course_id: mainLine.course_id || false,
                });
            }
        }

        return line;
    },
});
