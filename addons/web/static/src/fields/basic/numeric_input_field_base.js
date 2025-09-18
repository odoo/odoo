// @ts-check

/** @module @web/fields/basic/numeric_input_field_base - Abstract base class for numeric input fields with shared focus and parse logic */

import { Component, useState } from "@odoo/owl";
import { useInputField } from "@web/fields/input_field_hook";
import { useNumpadDecimal } from "@web/fields/numpad_decimal_hook";

/**
 * Base class for numeric input fields (integer, float, etc.).
 *
 * Provides shared infrastructure: hasFocus state, useInputField wiring
 * (getValue → formattedValue, parse via this.parse()), useNumpadDecimal,
 * focus event handlers, and the raw value getter.
 *
 * Subclasses must implement:
 *   - parse(value)       — parses the raw input string into a typed value
 *   - get formattedValue — returns the display value (format varies per type)
 */
export class NumericInputFieldBase extends Component {
    setup() {
        this.state = useState({ hasFocus: false });
        this.inputRef = useInputField({
            getValue: () => /** @type {any} */ (this).formattedValue,
            refName: "numpadDecimal",
            parse: (v) => /** @type {any} */ (this).parse(v),
        });
        useNumpadDecimal();
    }

    onFocusIn() {
        this.state.hasFocus = true;
    }

    onFocusOut() {
        this.state.hasFocus = false;
    }

    /** @returns {number | false} Raw field value from the record */
    get value() {
        return this.props.record.data[this.props.name];
    }
}
