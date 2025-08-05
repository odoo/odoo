import { Component } from "@odoo/owl";

export class StockValuationReportButtonsBar extends Component {
    static template = "stock_account.StockValuationReportButtonsBar";
    static props = {};

    onClickGenerateEntry() {
        return this.env.controller.actionGenerateEntry();
    }

    onClickPDF() {
        return this.env.controller.actionPrintReport("pdf");
    }

    onClickXLSX() {
        return this.env.controller.actionPrintReport("xlsx");
    }
}
