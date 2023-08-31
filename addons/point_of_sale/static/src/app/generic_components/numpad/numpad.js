/** @odoo-module */

import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";

/**
 * This generic components must have 12 or 16 buttons.
 * -> 12 will have 3 columns and 4 rows.
 * -> 16 will have 4 columns and 4 rows.
 * Because of the bootstrap class selection in the template, it will divide the number of buttons by 4.
 * (row-cols-{{ props.buttons.length / 4 }})
 */
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
