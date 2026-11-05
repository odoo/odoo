import { patch } from "@web/core/utils/patch";
import { GeneratePrinterData } from "@point_of_sale/app/utils/printer/generate_printer_data";

/**
 * This class is a JS copy of the class PosOrderReceipt in Python.
 */
patch(GeneratePrinterData.prototype, {
    get commonExtraData() {
        const extraData = super.commonExtraData;
        if (this.config.module_pos_restaurant) {
            const table = this.order.table_id;
            extraData.table_name = table?.table_number || false;
            extraData.floor_name = table?.floor_id?.name || false;
        }
        return extraData;
    },
    generateLineData() {
        const lines = super.generateLineData(...arguments);
        const order = this.order;
        if (!order.hasCourses()) {
            return lines;
        }
        // Mirror the order summary: lines grouped by course, the service fee at the very
        // bottom. The fee is moved to the last course once created, so its position in
        // the creation order says nothing about where it is displayed.
        const courseRank = new Map(order.courses.map((course, rank) => [course.id, rank]));
        const sortKeys = new Map(
            lines.map((line, index) => [
                line,
                [
                    line.is_service_fee_line ? 1 : 0,
                    courseRank.get(order.lines[index].course_id?.id) ?? -1,
                ],
            ])
        );
        return lines.toSorted((a, b) => {
            const [aFee, aRank] = sortKeys.get(a);
            const [bFee, bRank] = sortKeys.get(b);
            return aFee - bFee || aRank - bRank;
        });
    },
    generatePreparationData() {
        const receipts = super.generatePreparationData(...arguments);
        for (const receipt of receipts) {
            if (receipt.extra_data.table_name) {
                receipt.extra_data.order_label = false;
            }
        }
        return receipts;
    },
});
