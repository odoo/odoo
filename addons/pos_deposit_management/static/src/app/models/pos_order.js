import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/app/models/pos_order";

patch(PosOrder.prototype, {
    removeOrderline(line, deep = true) {
        const mainLine = line.deposit_main_line_id || line;
        const deposits = (deep ? mainLine.getAllLinesInCombo() : [mainLine]).map(
            (l) => l.depositLine
        );
        const result = super.removeOrderline(mainLine, deep);
        for (const deposit of deposits) {
            if (this.lines.includes(deposit)) {
                super.removeOrderline(deposit, false);
            }
        }
        return result;
    },
    sortDepositLines(lines) {
        const sorted = [];
        for (const line of lines) {
            if (lines.includes(line.deposit_main_line_id)) {
                continue;
            }
            sorted.push(line);
            const parent = line.combo_parent_id;
            const deposits = [
                line.combo_line_ids.length ? null : line.depositLine,
                parent?.combo_line_ids.at(-1) === line ? parent.depositLine : null,
            ];
            sorted.push(...deposits.filter((deposit) => lines.includes(deposit)));
        }
        return sorted;
    },
});
