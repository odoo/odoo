import { Component } from "@odoo/owl";
import { DateTimePicker } from "./datetime_picker";

/**
 * @typedef {import("./datetime_picker").DateTimePickerProps} DateTimePickerProps
 *
 * @typedef DateTimePickerPopoverProps
 * @property {() => void} close
 * @property {DateTimePickerProps} pickerProps
 */

/** @extends {Component<DateTimePickerPopoverProps>} */
export class DateTimePickerPopover extends Component {
    static components = { DateTimePicker };

    static props = {
        close: Function, // Given by the Popover service
        pickerProps: { type: Object, shape: DateTimePicker.props },
    };

    static template = "web.DateTimePickerPopover";

    get pickerProps() {
        return {
            ...this.props.pickerProps,
            focusTrap: true,
        };
    }
}
