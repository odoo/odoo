import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/app/models/pos_order";

patch(PosOrder.prototype, {
    removeOrderline(line, deep = true) {
        const mainLine = line.deposit_main_line_id || line;
        const group = deep ? mainLine.getAllLinesInCombo() : [mainLine];
        const deposits = group.map((l) => l.deposit_line_ids[0]).filter(Boolean);
        const result = super.removeOrderline(mainLine, deep);
        for (const deposit of deposits) {
            if (this.lines.includes(deposit)) {
                super.removeOrderline(deposit, false);
            }
        }
        return result;
    },

    getOrderlines() {
        const lines = super.getOrderlines();
        const isDeposit = (l) => l.deposit_main_line_id && lines.includes(l.deposit_main_line_id);
        const ordered = [];
        const pushWithDeposit = (line) => {
            ordered.push(line);
            const deposit = line.deposit_line_ids[0];
            if (deposit && lines.includes(deposit)) {
                ordered.push(deposit);
            }
        };
        for (const line of lines) {
            if (isDeposit(line)) {
                continue;
            }
            if (line.combo_parent_id && lines.includes(line.combo_parent_id)) {
                continue;
            }
            if (line.combo_line_ids?.length) {
                ordered.push(line);
                for (const child of line.combo_line_ids) {
                    if (lines.includes(child)) {
                        pushWithDeposit(child);
                    }
                }
                const deposit = line.deposit_line_ids[0];
                if (deposit && lines.includes(deposit)) {
                    ordered.push(deposit);
                }
                continue;
            }
            pushWithDeposit(line);
        }
        return ordered;
    },
});
