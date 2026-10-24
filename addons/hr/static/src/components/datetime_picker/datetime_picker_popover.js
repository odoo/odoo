import { t, useProps } from "@odoo/owl";
import { DateTimePickerPopover } from "@web/core/datetime/datetime_picker_popover";
import { dateTimePickerProps } from "@web/core/datetime/datetime_picker";
import { HrDateTimePicker } from "./datetime_picker";

export class HrDateTimePickerPopover extends DateTimePickerPopover {
    static components = { DateTimePicker: HrDateTimePicker };

    props = useProps({
        close: t.function(),
        pickerProps: t.object({
            ...dateTimePickerProps,
            showCreationModeToggle: t.boolean().optional(),
            creationMode: t.string().optional(),
            onCreationModeChange: t.function().optional(),
        }),
        showResetButton: t.boolean().optional(true),
    });
}
