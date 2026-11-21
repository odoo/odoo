import { patch } from "@web/core/utils/patch";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";

patch(PosOrderline.prototype, {
    update(vals) {
        const result = super.update(...arguments);
        if ("course_id" in vals) {
            this.syncCourseWithRelatedLines();
        }
        return result;
    },

    syncCourseWithRelatedLines() {
        const mainLine = this.deposit_main_line_id || this;
        const lines = mainLine.getAllLinesInCombo().flatMap((l) => [l, ...l.deposit_line_ids]);
        for (const line of lines) {
            if (line.course_id?.id !== this.course_id?.id) {
                line.update({ course_id: this.course_id || false });
            }
        }
    },
});
