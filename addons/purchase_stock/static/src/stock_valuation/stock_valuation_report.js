import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

import { StockValuationReport } from "@stock_account/stock_valuation/stock_valuation_report";


patch(StockValuationReport.prototype, {
    get accrual() {
        const accrual = super.accrual;
        const notInvoicedReceivedGoods = this.data.not_invoiced_received_goods;
        notInvoicedReceivedGoods.display_name = _t("Goods Received Not Invoiced");
        notInvoicedReceivedGoods.method = this.openPurchaseOrder.bind(this);
        notInvoicedReceivedGoods.index = accrual.lines.length;
        accrual.lines.push(this.data.not_invoiced_received_goods);
        accrual.value += this.data.not_invoiced_received_goods.value;
        this.purchaseOrderIds = notInvoicedReceivedGoods.lines.map((line) => line.id);
        return accrual;
    },

    // Getters -----------------------------------------------------------------
    get notInvoicedReceivedValuation() {
        return this.formatMonetary(this.data.not_invoiced_received_goods.value);
    },

    // On Click Methods --------------------------------------------------------
    openPurchaseOrder(line=false) {
        const action = {
            type: "ir.actions.act_window",
            name: _t("Purchase Orders"),
            res_model: "purchase.order",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        }
        if (line?.id) {
            action.views = [[false, "form"]],
            action.res_id = line.id;
        } else {
            action.domain = [["id", "in", this.purchaseOrderIds]];
        }
        return this.actionService.doAction(action);
    },
});
