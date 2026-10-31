import { patch } from "@web/core/utils/patch";
import { GeneratePrinterData } from "@point_of_sale/app/utils/printer/generate_printer_data";

patch(GeneratePrinterData.prototype, {
    generateLineData() {
        const lineData = super.generateLineData(...arguments);
        const dataByUuid = new Map(lineData.map((data) => [data.uuid, data]));
        const lineByUuid = new Map(this.order.lines.map((line) => [line.uuid, line]));
        const lines = lineData.map((data) => lineByUuid.get(data.uuid)).filter(Boolean);
        return this.order.sortDepositLines(lines).map((line) => {
            const data = dataByUuid.get(line.uuid);
            if (line.deposit_main_line_id?.combo_parent_id) {
                data.is_deposit_for_combo_child = true;
            }
            return data;
        });
    },
});
