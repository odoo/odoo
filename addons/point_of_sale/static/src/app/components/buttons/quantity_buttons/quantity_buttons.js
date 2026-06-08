import { Component, props, types } from "@odoo/owl";

export class QuantityButtons extends Component {
    static template = "point_of_sale.QuantityButtons";
    props = props({
        quantity: types.number(),
        setQuantity: types.function(),
        "isPlusButtonDisabled?": types.boolean(),
        "btnClasses?": types.string(),
    });

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
