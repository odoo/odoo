import { Component } from "@odoo/owl";
import { formatCurrency } from "@web/core/currency";

export class Orderline extends Component {
    static template = "point_of_sale.Orderline";
    static props = {
        line: Object,
        class: { type: Object, optional: true },
        slots: { type: Object, optional: true },
        showTaxGroupLabels: { type: Boolean, optional: true },
        showTaxGroup: { type: Boolean, optional: true },
        mode: { type: String, optional: true }, // display, receipt
        basic_receipt: { type: Boolean, optional: true },
    };
    static defaultProps = {
        showImage: false,
        showTaxGroupLabels: false,
        showTaxGroup: false,
        mode: "display",
        basic_receipt: false,
    };

    formatCurrency(amount) {
        return formatCurrency(amount, this.line.currency.id);
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
    get priceChange() {
        const oldUnitPrice = this.line.getOldUnitDisplayPrice()
            ? this.formatCurrency(this.line.getOldUnitDisplayPrice())
            : "";
        const price = this.line.getPriceString();

        return Boolean(
            this.line.price_type !== "original" ||
                this.line.getDiscount() != 0 ||
                (oldUnitPrice && oldUnitPrice !== price)
        );
    }
}
