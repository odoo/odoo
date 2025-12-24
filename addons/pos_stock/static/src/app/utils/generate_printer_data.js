import { patch } from "@web/core/utils/patch";
import { GeneratePrinterData } from "@point_of_sale/app/utils/printer/generate_printer_data";

/**
 * This class is a JS copy of the class PosOrderReceipt in Python.
 */
patch(GeneratePrinterData.prototype, {
    generateLineData() {
        return super.generateLineData().map((line, index) => {
            const orderLine = this.order.lines[index];
            line.lot_names = orderLine.pack_lot_ids?.length
                ? orderLine.pack_lot_ids.map((l) => l.lot_name)
                : false;
            return line;
        });
    },
    generateReceiptData() {
        const receiptData = super.generateReceiptData();
        receiptData.extra_data.formated_shipping_date = this.order.formatDateOrTime(
            "shipping_date",
            "date"
        );
        return receiptData;
    },
});
