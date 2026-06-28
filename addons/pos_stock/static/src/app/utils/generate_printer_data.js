import { patch } from "@web/core/utils/patch";
import { GeneratePrinterData } from "@point_of_sale/app/utils/printer/generate_printer_data";

/**
 * This class is a JS copy of the class PosOrderReceipt in Python.
 */
patch(GeneratePrinterData.prototype, {
    generateLineData() {
        return super.generateLineData().map((line, index) => {
            line.lot_names = this.order.lines[index].packLotLines;
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
