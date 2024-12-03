import { Component } from "@odoo/owl";
import { formatCurrency } from "@web/core/currency";

export class Orderline extends Component {
    static template = "point_of_sale.Orderline";
    static props = {
        line: Object,
        class: { type: Object, optional: true },
        showImage: { type: Boolean, optional: true },
        showTaxGroup: { type: Boolean, optional: true },
        slots: { type: Object, optional: true },
        mode: { type: String, optional: true }, // display, receipt
    };
    static defaultProps = {
        showImage: false,
        showTaxGroupLabels: false,
        mode: "display",
    };

    formatCurrency(amount) {
        return formatCurrency(amount, this.line.currency);
    }

    get line() {
        return this.props.line;
    }

    get taxGroup() {
        return [
            ...new Set(
                this.line.product_id.taxes_id
                    ?.map((tax) => tax.tax_group_id.pos_receipt_label)
                    .filter((label) => label)
            ),
        ].join(" ");
    }
}
