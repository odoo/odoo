import { formatDuration } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { statusBarField, StatusBarField } from "@web/views/fields/statusbar/statusbar_field";

export class StatusBarDurationField extends StatusBarField {
    static template = "mail.StatusBarDurationField";

    getAllItems() {
        /**
         * Calculates how many seconds have passed since the current stage started.
         *
         * Converts the stage start date to UTC and compares it with the current UTC time.
         */
        const items = super.getAllItems();
        const durationTracking = this.props.record.data.duration_tracking || {};
        if (Object.keys(durationTracking).length && durationTracking.d) {
            const { s: activeStageValue, d: activeStageStartDate } = durationTracking;
            const currentElapsedSeconds =
                luxon.DateTime.now().toSeconds() -
                luxon.DateTime.fromSQL(activeStageStartDate, { zone: "utc" }).toSeconds();
            for (const item of items) {
                let duration = durationTracking[item.value] || 0;
                if (activeStageValue === item.value) {
                    duration += currentElapsedSeconds;
                }
                if (duration > 0) {
                    item.shortTimeInStage = formatDuration(duration, false);
                    item.fullTimeInStage = formatDuration(duration, true);
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
