import { Component } from "@odoo/owl";
import { omit } from "../utils/objects";
import { DateTimePicker } from "./datetime_picker";
import { useDateTimePicker } from "./datetime_picker_hook";

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
        const getPickerProps = () => omit(this.props, ...Object.keys(dateTimeInputOwnProps));

        useDateTimePicker({
            format: this.props.format,
            showSeconds: this.props.rounding <= 0,
            get pickerProps() {
                return getPickerProps();
            },
            onApply: (...args) => this.props.onApply?.(...args),
            onChange: (...args) => this.props.onChange?.(...args),
        });
    }
}
