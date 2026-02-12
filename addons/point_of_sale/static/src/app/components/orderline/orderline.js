import { Component, useRef } from "@odoo/owl";
import { useTimedPress } from "@point_of_sale/app/utils/use_timed_press";
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
        return this.line.taxGroupLabels;
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
