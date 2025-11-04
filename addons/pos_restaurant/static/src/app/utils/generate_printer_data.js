import { patch } from "@web/core/utils/patch";
import { GeneratePrinterData } from "@point_of_sale/app/utils/generate_printer_data";

/**
 * This class is a JS copy of the class PosOrderReceipt in Python.
 */
patch(GeneratePrinterData.prototype, {
    generateData() {
        const data = super.generateData(...arguments);

        if (this.config.module_pos_restaurant) {
            data.extra_data.table_name = this.order.table_id?.table_number || false;
        }

        return data;
    },
});
