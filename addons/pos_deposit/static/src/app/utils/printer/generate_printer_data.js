import { sortDepositLines } from "@pos_deposit/app/utils/sort_deposit_lines";
import { patch } from "@web/core/utils/patch";
import { GeneratePrinterData } from "@point_of_sale/app/utils/printer/generate_printer_data";

patch(GeneratePrinterData.prototype, {
    generateReceiptData() {
        const receiptData = super.generateReceiptData();
        if (!this.config.module_pos_deposit) {
            return receiptData;
        }
        const sortedLines = sortDepositLines(this.order.getOrderlines());
        const positionByUuid = new Map(sortedLines.map((line, position) => [line.uuid, position]));
        const getPosition = (lineData) => positionByUuid.get(lineData.uuid) ?? sortedLines.length;
        receiptData.lines.sort((lineA, lineB) => getPosition(lineA) - getPosition(lineB));
        for (const lineData of receiptData.lines) {
            const orderline = sortedLines[positionByUuid.get(lineData.uuid)];
            const mainLine = orderline?.deposit_main_line_id;
            if (mainLine) {
                lineData.is_deposit_line = true;
                lineData.is_combo_child_deposit = Boolean(mainLine.combo_parent_id);
            }
        }
        return receiptData;
    },
});
