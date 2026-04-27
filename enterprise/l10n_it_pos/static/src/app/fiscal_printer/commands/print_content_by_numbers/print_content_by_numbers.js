import { Component } from "@odoo/owl";

export class PrintContentByNumbers extends Component {
    static template = "l10n_it_pos.PrintContentByNumbers";
    static props = {
        order: {
            type: Object,
        },
    };

    setup() {
        this.receiptNumber = this.props.order.it_fiscal_receipt_number;
        const dateParts = this.props.order.it_fiscal_receipt_date.split("/");
        this.day = dateParts[0];
        this.month = dateParts[1];
        this.year = dateParts[2];
    }
}
