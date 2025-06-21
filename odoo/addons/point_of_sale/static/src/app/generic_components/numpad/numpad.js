/** @odoo-module */

import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";

export class Numpad extends Component {
    static template = "point_of_sale.Numpad";
    static props = {
        class: { type: String, optional: true },
        onClick: { type: Function, optional: true },
        buttons: {
            type: Array,
            element: {
                type: Object,
                shape: {
                    value: String,
                    text: { type: String, optional: true },
                    class: { type: String, optional: true },
                    disabled: { type: Boolean, optional: true },
                },
            },
        },
    };
    static defaultProps = {
        class: "",
    };
    setup() {
        if (!this.props.onClick) {
            this.numberBuffer = useService("number_buffer");
            this.onClick = (buttonValue) => this.numberBuffer.sendKey(buttonValue);
        } else {
            this.onClick = this.props.onClick;
        }
    }
}
