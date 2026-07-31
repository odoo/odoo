import { Component } from "@odoo/owl";

export class StockValuationReportButtonsBar extends Component {
    static template = "account.StockValuationReportButtonsBar";
    static props = {};

    onClickGenerateEntries() {
        return this.env.controller.actionGenerateEntries();
    }
}
