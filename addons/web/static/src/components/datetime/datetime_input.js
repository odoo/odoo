// @ts-check

/** @module @web/components/datetime/datetime_input - Date/time text input component that opens a DateTimePicker popover */

import { Component } from "@odoo/owl";
import { omit } from "@web/core/utils/collections/objects";

import { DateTimePicker } from "./datetime_picker";
import { useDateTimePicker } from "./datetime_picker_hook";
/** @typedef {luxon["DateTime"]["prototype"]} DateTime */

/**
 * @typedef {import("./datetime_picker").DateTimePickerProps & {
 *  format?: string;
 *  id?: string;
 *  onApply?: (value: DateTime) => any;
 *  onChange?: (value: DateTime) => any;
 *  placeholder?: string;
 * }} DateTimeInputProps
 */

const dateTimeInputOwnProps = {
    format: { type: String, optional: true },
    id: { type: String, optional: true },
    class: { type: String, optional: true },
    onChange: { type: Function, optional: true },
    onApply: { type: Function, optional: true },
    placeholder: { type: String, optional: true },
    disabled: { type: Boolean, optional: true },
};

/** @extends {Component<DateTimeInputProps>} */
export class DateTimeInput extends Component {
    static props = {
        ...DateTimePicker.props,
        ...dateTimeInputOwnProps,
    };

    static template = "web.DateTimeInput";

    setup() {
        const getPickerProps = () =>
            omit(
                this.props,
                .../** @type {any} */ (Object.keys(dateTimeInputOwnProps)),
            );

        useDateTimePicker(
            /** @type {any} */ ({
                format: this.props.format,
                showSeconds: this.props.rounding <= 0,
                get pickerProps() {
                    return getPickerProps();
                },
                onApply: (/** @type {any} */ value) => this.props.onApply?.(value),
                onChange: (/** @type {any} */ value) => this.props.onChange?.(value),
            }),
        );
    }
}
