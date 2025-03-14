import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { DateTimePicker } from "./datetime_picker";

/**
 * Bottom sheet component for displaying a datetime picker on mobile
 *
 * @extends {Component}
 */
export class DateTimePickerBottomSheet extends Component {
    static components = { DateTimePicker };
    static template = "web.DateTimePickerBottomSheet";

    static props = {
        close: Function,
        pickerProps: { type: Object, optional: true },
    };


    /**
     * Apply selection and close the sheet
     */
    onApply() {
        this.props.close();
    }
}

// Register this component as the bottom sheet alternative for DateTimePickerPopover
registry.category("bottom_sheet_components").add(
    "DateTimePickerPopover",
    {
        Component: DateTimePickerBottomSheet,
        slots: {
            header: "header" // doesn't work :(
        },
        options: {
            initialHeightPercent: 60,
            maxHeightPercent: 95,
            withBodyPadding: false,
            startExpanded: true,
        }
    }
);
