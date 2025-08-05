import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

import { StockValuationReport } from "@stock_account/stock_valuation/stock_valuation_report";


patch(StockValuationReport.prototype, {
    get accrual() {
        const accrual = super.accrual;
        const notInvoicedDeliveredGoods = this.data.not_invoiced_delivered_goods;
        notInvoicedDeliveredGoods.display_name = _t("Goods Delivered Not Invoiced");
        notInvoicedDeliveredGoods.method = this.openSaleOrder.bind(this);
        notInvoicedDeliveredGoods.index = accrual.lines.length;
        accrual.value += notInvoicedDeliveredGoods.value;
        accrual.lines.push(notInvoicedDeliveredGoods);
        this.saleOrderIds = notInvoicedDeliveredGoods.lines.map((line) => line.id);
        return accrual;
    },

    // On Click Methods --------------------------------------------------------
    openSaleOrder(line=false) {
        const action = {
            type: "ir.actions.act_window",
            name: _t("Sale Orders"),
            res_model: "sale.order",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        }
        if (line?.id) {
            action.views = [[false, "form"]],
            action.res_id = line.id;
        } else {
            action.domain = [["id", "in", this.saleOrderIds]];
        }
        return this.actionService.doAction(action);
    },
});
