import { GeneratePrinterData } from "@point_of_sale/app/utils/printer/generate_printer_data";
import { patch } from "@web/core/utils/patch";

patch(GeneratePrinterData.prototype, {
    generateLineData() {
        const linesData = super.generateLineData();
        return linesData.map((lineData, index) => {
            lineData.is_discount_line = this.order.lines[index].isDiscountLine;
            return lineData;
        });
    },
});
