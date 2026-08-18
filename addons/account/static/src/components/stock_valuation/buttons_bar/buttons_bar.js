import { Component } from "@odoo/owl";

export class StockValuationReportButtonsBar extends Component {
    static template = "account.StockValuationReportButtonsBar";
    static props = {};

    onClickGenerateEntry() {
        return this.env.controller.actionGenerateEntry();
    }
}
