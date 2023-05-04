/** @odoo-module **/

import { Component } from "@odoo/owl";
import { omit } from "../utils/objects";
import { useDateTimePicker } from "./datetime_hook";
import { DateTimePicker } from "./datetime_picker";

/**
 * @typedef {import("./datetime_picker").DateTimePickerProps & {
 *  format?: string;
 *  id?: string;
 *  onApply?: (value: DateTime) => any;
 *  onChange?: (value: DateTime) => any;
 *  placeholder?: string;
 * }} DateTimeInputProps
 */

/** @extends {Component<DateTimeInputProps>} */
export class DateTimeInput extends Component {
    static props = {
        ...DateTimePicker.props,
        format: { type: String, optional: true },
        id: { type: String, optional: true },
        onChange: { type: Function, optional: true },
        onApply: { type: Function, optional: true },
        placeholder: { type: String, optional: true },
    };

    static template = "web.DateTimeInput";

    setup() {
        useDateTimePicker({
            format: this.props.format,
            pickerProps: (props) =>
                omit(props, "format", "placeholder", "id", "onChange", "onApply"),
            onApply: (...args) => this.props.onApply?.(...args),
            onChange: (...args) => this.props.onChange?.(...args),
        });
    }
}
