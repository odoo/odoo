import { Component } from "@odoo/owl";

export class TaxTagPopup extends Component {
    static template = "account.tax_tag_popover_template";
    static props = {
        description: { type: String, optional: true },
        invoiceLines: { type: Array, optional: true },
        refundLines: { type: Array, optional: true },
        close: { type: Function, optional: true },
    };
}
