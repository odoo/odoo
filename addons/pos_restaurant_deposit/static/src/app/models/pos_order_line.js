import { patch } from "@web/core/utils/patch";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";

patch(PosOrderline.prototype, {
    update(vals) {
        const result = super.update(...arguments);

        if (!("course_id" in vals)) {
            return result;
        }

        const linesToUpdate = new Set();
        const mainLine = this.deposit_main_line_id || this;
        linesToUpdate.add(mainLine);

        if (mainLine.depositLine) {
            linesToUpdate.add(mainLine.depositLine);
        }

        if (mainLine.combo_line_ids?.length) {
            for (const child of mainLine.combo_line_ids) {
                linesToUpdate.add(child);

                if (child.depositLine) {
                    linesToUpdate.add(child.depositLine);
                }
            }
        }

        if (mainLine.combo_parent_id) {
            const parent = mainLine.combo_parent_id;
            linesToUpdate.add(parent);

            if (parent.depositLine) {
                linesToUpdate.add(parent.depositLine);
            }
        }

        for (const relatedLine of linesToUpdate) {
            if (relatedLine !== this && relatedLine.course_id?.id !== this.course_id?.id) {
                relatedLine.update({
                    course_id: this.course_id,
                });
            }
        }

        return result;
    },
});
