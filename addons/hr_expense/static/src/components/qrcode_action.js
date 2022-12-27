/** @odoo-module */

import { registry } from "@web/core/registry";
import { Component, xml } from "@odoo/owl";

const actionRegistry = registry.category("actions");

class QRModalComponent extends Component {
    setup() {
        this.url = _.str.sprintf(
            "/report/barcode/?barcode_type=QR&value=%s&width=256&height=256&humanreadable=1",
            this.props.action.params.url);
    }
}

QRModalComponent.template = xml`
        <div style="text-align:center;" class="o_expense_modal">
            <t t-if="url">
                <h3>Scan this QR code to get the Odoo app:</h3><br/><br/>
                <img class="border border-dark rounded" t-att-src="url"/>
            </t>
        </div>`;

actionRegistry.add("expense_qr_code_modal", QRModalComponent);
