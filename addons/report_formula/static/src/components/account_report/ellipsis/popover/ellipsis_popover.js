/** @odoo-module native */
import { Component } from "@odoo/owl";

export class AccountReportEllipsisPopover extends Component {
    static template = "report_formula.AccountReportEllipsisPopover";
    static props = {
        close: Function,
        name: String,
        copyEllipsisText: Function,
    };
}
