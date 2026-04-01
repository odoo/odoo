import { Component } from "@odoo/owl";

export class QuantityButtons extends Component {
    static template = "point_of_sale.QuantityButtons";
    static props = {
        quantity: Number,
        setQuantity: Function,
        isPlusButtonDisabled: { type: Boolean, optional: true },
        btnClasses: { type: String, optional: true },
    };

    changeQuantity(increment) {
        const isDisabled = increment == 1 && this.props.isPlusButtonDisabled;
        if (!isDisabled) {
            this.props.setQuantity(this.props.quantity + increment);
        }
    }

    setQuantity(event) {
        const quantity = parseFloat(event.target.value);
        this.props.setQuantity(isNaN(quantity) ? 0 : quantity);
    }
}
