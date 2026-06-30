import { Component, props, t } from "@odoo/owl";
import { TimePicker, timePickerProps } from "./time_picker";

/**
 * @typedef {import("./time_picker").TimePickerProps} TimePickerProps
 *
 * @typedef TimePickerPopoverProps
 * @property {() => void} close
 * @property {TimePickerProps} pickerProps
 */

/** @extends {Component<TimePickerPopoverProps>} */
export class TimePickerPopover extends Component {
    static components = { TimePicker };

    props = props({
        close: t.function(), // Given by the Popover service
        pickerProps: t.object(timePickerProps),
    });

    static template = "web.TimePickerPopover";
}
