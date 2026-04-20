import { Component, props, t } from "@odoo/owl";
import { useHotkey } from "../hotkeys/hotkey_hook";
import { DateTimePicker, dateTimePickerProps } from "./datetime_picker";

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

    props = props({
        close: t.function(), // Given by the Popover service
        pickerProps: t.object(dateTimePickerProps),
        showResetButton: t.boolean().optional(true),
    });

    static template = "web.DateTimePickerPopover";

    //-------------------------------------------------------------------------
    // Lifecycle
    //-------------------------------------------------------------------------

    setup() {
        useHotkey("enter", () => this.props.close());
    }
}
