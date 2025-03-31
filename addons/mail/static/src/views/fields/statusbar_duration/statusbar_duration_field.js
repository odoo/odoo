import { formatDuration } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { statusBarField, StatusBarField } from "@web/views/fields/statusbar/statusbar_field";

export class StatusBarDurationField extends StatusBarField {
    static template = "mail.StatusBarDurationField";

    getAllItems() {
        const items = super.getAllItems();
        const durationTracking = this.props.record.data.duration_tracking || {};
        if (Object.keys(durationTracking).length) {
            for (const item of items) {
                const duration = durationTracking[item.value];
                if (duration > 0) {
                    item.shortTimeInStage = formatDuration(duration, false);
                    item.fullTimeInStage = formatDuration(duration, true);
                } else {
                    item.shortTimeInStage = 0;
                }
            }
        }
        return items;
    }
}

export const statusBarDurationField = {
    ...statusBarField,
    component: StatusBarDurationField,
    displayName: _t("Status with time"),
    supportedTypes: ["many2one"],
    fieldDependencies: [{ name: "duration_tracking", type: "JSON" }],
};

registry.category("fields").add("statusbar_duration", statusBarDurationField);
