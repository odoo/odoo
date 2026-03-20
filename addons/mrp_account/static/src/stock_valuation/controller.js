import { patch } from "@web/core/utils/patch";

import { StockValuationReportController } from "@stock_account/stock_valuation/controller";

patch(StockValuationReportController.prototype, {
    async loadReportData() {
        const data = await super.loadReportData();
        if (this.data.cost_of_production) {
            // Prepare the "Cost of Production" lines.
            for (const line of this.data.cost_of_production.lines) {
                line.account = this.data.accounts_by_id[line.account_id];
            }
        }
        return data;
    },
});
