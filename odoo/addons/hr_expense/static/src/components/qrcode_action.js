/** @odoo-module */

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { sprintf } from "@web/core/utils/strings";


const actionRegistry = registry.category("actions");

class QRModalComponent extends Component {
    setup() {
        this.url = sprintf(
            "/report/barcode/?barcode_type=QR&value=%s&width=256&height=256&humanreadable=1",
            this.props.action.params.url);
    }
}

QRModalComponent.template = "hr_expense.QRModalComponent"

actionRegistry.add("expense_qr_code_modal", QRModalComponent);
