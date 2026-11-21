import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/app/models/pos_order";

patch(PosOrder.prototype, {
    _isItemCountExcludedLine(line) {
        return super._isItemCountExcludedLine(line) || line.product_id.product_tmpl_id.is_deposit;
    },
    removeOrderline(line, deep = true) {
        const mainLine = line.deposit_main_line_id || line;
        const mainLines = deep ? mainLine.getAllLinesInCombo() : [mainLine];
        const depositLines = mainLines.flatMap((l) => l.deposit_line_ids);
        const result = super.removeOrderline(mainLine, deep);
        for (const depositLine of depositLines) {
            super.removeOrderline(depositLine, false);
        }
        return result;
    },
});
