import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

import { StockValuationReport } from "@account/components/stock_valuation/stock_valuation_report";


patch(StockValuationReport.prototype, {
    openStockMoveView(title, usage) {
        const domain = [
            "|",
            ["location_id.usage", "=", usage],
            ["location_dest_id.usage", "=", usage],
        ];
        if (this.controller.dateAsString) {
            domain.unshift("&");
            domain.push(["date", "<=", this.controller.dateAsString]);
        }
        return this.actionService.doAction({
            name: title,
            type: "ir.actions.act_window",
            res_model: "stock.move",
            domain,
            views: [[false, 'list'], [false, 'form']],
            target: 'current',
        });
    },

    openInventoryLoss() {
        return this.openStockMoveView(_t("Inventory Loss"), "inventory");
    },
});
