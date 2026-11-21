import { sortDepositLines } from "@pos_deposit/app/utils/sort_deposit_lines";
import { patch } from "@web/core/utils/patch";
import { GeneratePrinterData } from "@point_of_sale/app/utils/printer/generate_printer_data";

patch(GeneratePrinterData.prototype, {
    generateLineData() {
        const lineData = super.generateLineData();
        const lines = this.order.getOrderlines();
        const dataByLine = new Map(lines.map((line, index) => [line, lineData[index]]));
        return sortDepositLines(lines).map((line) => {
            const data = dataByLine.get(line);
            const mainLine = line.deposit_main_line_id;
            if (mainLine) {
                data.is_deposit_line = true;
                data.is_combo_child_deposit = Boolean(mainLine.combo_parent_id);
            }
            return data;
        });
    },
});
