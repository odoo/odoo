import { Component } from "@odoo/owl";

import { registry } from "@web/core/registry";
import { sprintf } from "@web/core/utils/strings";

const actionRegistry = registry.category("actions");

class QRModalComponent extends Component {
    static props = {
        action: Object,
        actionId: { type: Number, optional: true },
        className: { type: String, optional: true },
    };
    static template = "hr_expense.QRModalComponent";

    setup() {
        this.url = sprintf(
            "/report/barcode/?barcode_type=QR&value=%s&width=256&height=256&humanreadable=1",
            this.props.action.params.url);
    }
}

actionRegistry.add("expense_qr_code_modal", QRModalComponent);
