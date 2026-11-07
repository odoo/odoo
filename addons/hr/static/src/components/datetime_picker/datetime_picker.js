import { t, useProps } from "@odoo/owl";
import { DateTimePicker } from "@web/core/datetime/datetime_picker";

export class HrDateTimePicker extends DateTimePicker {
    static template = "hr.DateTimePicker";

    versionDateTimePickerProps = useProps({
        showCreationModeToggle: t.boolean().optional(),
        creationMode: t.string().optional(),
        onCreationModeChange: t.function().optional(),
    });
}
