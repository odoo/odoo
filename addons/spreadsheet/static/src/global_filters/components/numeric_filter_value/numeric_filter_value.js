/** @odoo-module native */
/** @ts-check */

import { Component, useEffect, useRef } from "@odoo/owl";
import { parseFloat } from "@web/core/parsers";
import { useNumpadDecimal } from "@web/fields/numpad_decimal_hook";

export class NumericFilterValue extends Component {
    static template = "spreadsheet.NumericFilterValue";
    static props = {
        onValueChanged: Function,
        value: { type: [Number, String], optional: true },
    };

    setup() {
        useNumpadDecimal();
        this.inputRef = useRef("numpadDecimal");
        // The template deliberately does not bind the input to the prop. OWL
        // treats `value` on an input as a DOM property and wraps it in a fresh
        // `new String(...)` to defeat its own equality check, so a
        // `t-att-value` rewrites the box on EVERY render and eats whatever the
        // user is halfway through typing. We push the value in ourselves, and
        // never over a box that has the focus -- same shape as `useInputField`
        // in `web/static/src/fields/input_field_hook.js`.
        useEffect(
            (el, value) => {
                if (!el || el === document.activeElement) {
                    return;
                }
                const text = value ?? "";
                if (el.value !== String(text)) {
                    el.value = text;
                }
            },
            () => [this.inputRef.el, this.props.value],
        );
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
