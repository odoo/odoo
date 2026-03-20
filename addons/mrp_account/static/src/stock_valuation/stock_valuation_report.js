import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

import { StockValuationReport } from "@stock_account/stock_valuation/stock_valuation_report";


patch(StockValuationReport.prototype, {
    openCostOfProduction() {
        return this.openStockMoveView(_t("Cost of Production"), "production");
    }
});
