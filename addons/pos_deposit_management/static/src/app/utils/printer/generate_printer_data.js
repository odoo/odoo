import { patch } from "@web/core/utils/patch";
import { GeneratePrinterData } from "@point_of_sale/app/utils/printer/generate_printer_data";

patch(GeneratePrinterData.prototype, {
    generateLineData() {
        const lineData = super.generateLineData(...arguments);
        const lineByUuid = {};
        for (const line of this.order.lines) {
            lineByUuid[line.uuid] = line;
        }
        const dataByUuid = {};
        for (const data of lineData) {
            dataByUuid[data.uuid] = data;
        }

        for (const data of lineData) {
            const line = lineByUuid[data.uuid];
            const mainLine = line?.deposit_main_line_id;
            if (mainLine?.combo_parent_id) {
                data.is_deposit_for_combo_child = true;
                data.deposit_main_line_id = mainLine.uuid;
                data.deposit_main_line_combo_parent_id = mainLine.combo_parent_id.uuid;
            }
        }

        const ordered = [];
        const placed = new Set();
        const push = (line) => {
            const data = dataByUuid[line?.uuid];
            if (data && !placed.has(line.uuid)) {
                placed.add(line.uuid);
                ordered.push(data);
            }
        };
        const pushDeposit = (line) => {
            const deposit = line.deposit_line_ids?.[0];
            if (deposit) {
                push(deposit);
            }
        };

        for (const data of lineData) {
            const line = lineByUuid[data.uuid];
            if (!line || placed.has(line.uuid)) {
                continue;
            }
            if (line.deposit_main_line_id || line.combo_parent_id) {
                continue;
            }
            push(line);
            for (const child of line.combo_line_ids || []) {
                push(child);
                pushDeposit(child);
            }
            pushDeposit(line);
        }
        for (const data of lineData) {
            if (!placed.has(data.uuid)) {
                placed.add(data.uuid);
                ordered.push(data);
            }
        }
        return ordered;
    },
});
