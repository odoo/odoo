import { registry } from "@web/core/registry";
import { RadioField, radioField } from "@web/views/fields/radio/radio_field";
import { _t } from "@web/core/l10n/translation";

export class WorkEntrySourceField extends RadioField {
    static template = "hr_work_entry.WorkEntrySourceField";

    get isFullyFlexible() {
        return !this.props.record.data.resource_calendar_id;
    }

    get tooltipWarning() {
        return JSON.stringify({
            "text" : _t("Invalid option: For fully flexible calendars, the work entry source cannot be 'Working Hours'."),
        })
    }
}

export const workEntrySourceField = {
    ...radioField,
    component: WorkEntrySourceField,
    fieldDependencies: [
        { name: "resource_calendar_id", type: "many2one", relation: "resource.calendar" },
    ],
};

registry.category("fields").add("work_entry_source_field", workEntrySourceField);
