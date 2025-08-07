import { Component, useRef } from "@odoo/owl";
import { useTimedPress } from "@point_of_sale/app/utils/use_timed_press";
import { formatCurrency } from "@web/core/currency";
import { TagsList } from "@web/core/tags_list/tags_list";

export class Orderline extends Component {
    static components = { TagsList };
    static template = "point_of_sale.Orderline";
    static props = {
        line: Object,
        class: { type: Object, optional: true },
        slots: { type: Object, optional: true },
        showTaxGroupLabels: { type: Boolean, optional: true },
        showTaxGroup: { type: Boolean, optional: true },
        mode: { type: String, optional: true }, // display, receipt
        basic_receipt: { type: Boolean, optional: true },
        onClick: { type: Function, optional: true },
        onLongPress: { type: Function, optional: true },
    };
    static defaultProps = {
        showImage: false,
        showTaxGroupLabels: false,
        showTaxGroup: false,
        mode: "display",
        basic_receipt: false,
        onClick: () => {},
        onLongPress: () => {},
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
    getInternalNotes() {
        return JSON.parse(this.line.note || "[]");
    }

    setup() {
        this.root = useRef("root");
        if (this.props.mode === "display") {
            useTimedPress(this.root, [
                {
                    type: "release",
                    maxDelay: 500,
                    callback: (event, duration) => {
                        this.props.onClick(event, duration);
                    },
                },
                {
                    type: "hold",
                    delay: 500,
                    callback: (event, duration) => {
                        this.props.onLongPress(event, duration);
                    },
                },
            ]);
        }
    }
}
