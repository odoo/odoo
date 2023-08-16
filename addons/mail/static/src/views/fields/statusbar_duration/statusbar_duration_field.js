/** @odoo-module **/

import { formatDuration } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import {
    preloadStatusBar,
    statusBarField,
    StatusBarField,
} from "@web/views/fields/statusbar/statusbar_field";

export class StatusBarDurationField extends StatusBarField {
    static template = "mail.StatusBarDurationField";

    computeItems(grouped = true) {
        const items = super.computeItems(grouped);
        if (!grouped) {
            return items;
        }
        if (this.props.record.data.duration_tracking) {
            for (const property in items) {
                this.setStatusbarDuration(items[property]);
            }
        }
        return items;
    }

    setStatusbarDuration(stages) {
        const durationTracking = this.props.record.data.duration_tracking;
        if (!Object.keys(durationTracking).length) {
            return;
        }
        for (const stage of stages) {
            if (stage.id in durationTracking && durationTracking[stage.id] > 0) {
                stage.shortTimeInStage = formatDuration(durationTracking[stage.id], false);
                stage.fullTimeInStage = formatDuration(durationTracking[stage.id], true);
            } else {
                stage.shortTimeInStage = false;
            }
        }
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

registry.category("preloadedData").add("statusbar_duration", {
    loadOnTypes: ["many2one"],
    extraMemoizationKey: (record, fieldName) => {
        return record.data[fieldName];
    },
    preload: preloadStatusBar,
});
