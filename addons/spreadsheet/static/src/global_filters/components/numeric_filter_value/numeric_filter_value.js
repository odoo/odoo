/** @ts-check */

import { Component, useRef } from "@odoo/owl";
import { useNumpadDecimal } from "@web/views/fields/numpad_decimal_hook";
import { parseFloat } from "@web/views/fields/parsers";

export class NumericFilterValue extends Component {
    static template = "spreadsheet.NumericFilterValue";
    static props = {
        onValueChanged: Function,
        value: { type: [Number, String], optional: true },
    };

    setup() {
        useNumpadDecimal();
        this.inputRef = useRef("numpadDecimal");
    }

    onChange(value) {
        let numericValue;
        if (value === undefined || value === "") {
            numericValue = undefined;
        } else {
            try {
                numericValue = parseFloat(value);
                // eslint-disable-next-line no-unused-vars
            } catch (e) {
                numericValue = 0;
            }
        }
        this.props.onValueChanged(numericValue);
        // If the user enters a non-numeric string, we default the value to 0.
        // However, if the same invalid input is entered again, the component
        // doesn't re-render because the prop value hasn't changed. To ensure
        // the input reflects the correct state, we manually set the input
        // element's value to 0.
        if (numericValue === 0 && this.inputRef?.el) {
            this.inputRef.el.value = 0;
        }
    }
}
