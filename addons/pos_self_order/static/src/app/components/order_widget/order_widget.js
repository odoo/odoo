import { Component } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";

export class OrderWidget extends Component {
    static template = "pos_self_order.OrderWidget";
    static props = {
        buttons: {
            type: Array,
            element: {
                type: Object,
                shape: {
                    position: {
                        type: String,
                        validator: (value) => ["left", "right"].includes(value),
                    },
                    label: { type: String },
                    onClick: { type: Function },
                    severity: { type: String },
                    icon: { type: String, optional: true },
                    extraClasses: { type: String, optional: true },
                    disabled: { type: Boolean, optional: true },
                },
            },
        },
        total: {
            type: Object,
            optional: true,
            shape: {
                count: { type: Number },
                price: { type: Number },
                onClick: { type: Function },
            },
        },
        removeTopClasses: { type: Boolean, optional: true },
    };

    setup() {
        this.selfOrder = useSelfOrder();
    }

    getButtons(position) {
        return this.props.buttons.filter((button) => button.position === position);
    }
}
