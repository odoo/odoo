/** @odoo-module */

import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class OrderImportPopup extends Component {
    static template = "point_of_sale.OrderImportPopup";
    static components = { Dialog };
    static props = {
        report: Object,
    };

    get unpaidSkipped() {
        return (
            (this.props.report.unpaid_skipped_existing || 0) +
            (this.props.report.unpaid_skipped_session || 0)
        );
    }
}
