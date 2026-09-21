/** @odoo-module native */
import { Component } from "@odoo/owl";

export class AccountReportDebugPopover extends Component {
    static template = "report_formula.AccountReportDebugPopover";
    static props = {
        close: Function,
        expressionsDetail: Array,
        onClose: Function,
    };
}
