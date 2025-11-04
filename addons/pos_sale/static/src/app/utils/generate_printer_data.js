import { patch } from "@web/core/utils/patch";
import { GeneratePrinterData } from "@point_of_sale/app/utils/generate_printer_data";

/**
 * This class is a JS copy of the class PosOrderReceipt in Python.
 */
patch(GeneratePrinterData.prototype, {
    generateLineData() {
        const data = super.generateLineData(...arguments);
        for (const index in this.order.lines) {
            const line = this.order.lines[index];
            const lineData = data[index];
            lineData.sale_order_name = line.sale_order_origin_id?.name || false;
        }
        return data;
    },
});
