import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/app/models/pos_order";

patch(PosOrder.prototype, {
    removeOrderline(line, deep = true) {
        const mainLine = line._mainLine || line;
        const group = deep ? mainLine.getAllLinesInCombo() : [mainLine];
        const deposits = group.map((l) => l._depositLine).filter(Boolean);
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
        const isDeposit = (l) => l._mainLine && lines.includes(l._mainLine);
        const ordered = [];
        for (const line of lines) {
            if (isDeposit(line)) {
                continue;
            }
            ordered.push(line);
            if (line._depositLine && lines.includes(line._depositLine)) {
                ordered.push(line._depositLine);
            }
        }
        return ordered;
    },
});
