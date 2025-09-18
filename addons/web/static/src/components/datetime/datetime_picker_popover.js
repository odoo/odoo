// @ts-check

/** @module @web/components/datetime/datetime_picker_popover - Popover wrapper that hosts a DateTimePicker with keyboard dismiss support */

import { Component } from "@odoo/owl";
import { useHotkey } from "@web/services/hotkeys/hotkey_hook";

import { DateTimePicker } from "./datetime_picker";
/** @import { DateTimePickerProps } from "./datetime_picker" */

/**
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

    //-------------------------------------------------------------------------
    // Lifecycle
    //-------------------------------------------------------------------------

    setup() {
        useHotkey("enter", () => this.props.close());
    }
}
