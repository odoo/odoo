import { Component, props, t } from "@odoo/owl";
// import { omit } from "../utils/objects";
import { dateTimePickerProps } from "./datetime_picker";
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
    format: t.string().optional(),
    id: t.string().optional(),
    class: t.string().optional(),
    onChange: t.function().optional(),
    onApply: t.function().optional(),
    placeholder: t.string().optional(),
    disabled: t.boolean().optional(),
};

/** @extends {Component<DateTimeInputProps>} */
export class DateTimeInput extends Component {
    props = props({
        ...dateTimeInputOwnProps,
    });
    pickerProps = props(dateTimePickerProps);
    static template = "web.DateTimeInput";

    setup() {
        // const getPickerProps = () => omit(this.props, ...Object.keys(dateTimeInputOwnProps));
        const pickerProps = this.pickerProps;
        useDateTimePicker({
            format: this.props.format,
            showSeconds: this.props.rounding <= 0,
            get pickerProps() {
                return pickerProps;
            },
            onApply: (...args) => this.props.onApply?.(...args),
            onChange: (...args) => this.props.onChange?.(...args),
        });
    }
}
