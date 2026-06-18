import { Component, props, t } from "@odoo/owl";

export class QuantityButtons extends Component {
    static template = "point_of_sale.QuantityButtons";
    props = props({
        quantity: t.number(),
        setQuantity: t.function(),
        isPlusButtonDisabled: t.boolean().optional(),
        btnClasses: t.string().optional(),
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
