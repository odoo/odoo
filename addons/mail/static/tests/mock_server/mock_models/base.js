import { getKwArgs, models } from "@web/../tests/web_test_helpers";
import { patch } from "@web/core/utils/patch";

patch(models.ServerModel.prototype, {
    /**
     * @override
     * @type {typeof models.ServerModel["prototype"]["get_views"]}
     */
    get_views() {
        const result = super.get_views(...arguments);
        for (const modelName of Object.keys(result.models)) {
            if (this.has_activities) {
                result.models[modelName].has_activities = true;
            }
        }
        return result;
    },
});

export class Base extends models.ServerModel {
    _name = "base";

    /**
     * @param {Object} trackedFieldNamesToField
     * @param {Object} initialTrackedFieldValues
     * @param {Object} record
     */
    _mail_track(trackedFieldNamesToField, initialTrackedFieldValues, record) {
        const kwargs = getKwArgs(
            arguments,
            "trackedFieldNamesToField",
            "initialTrackedFieldValues",
            "record"
        );
        trackedFieldNamesToField = kwargs.trackedFieldNamesToField;
        initialTrackedFieldValues = kwargs.initialTrackedFieldValues;
        record = kwargs.record;

        /** @type {import("mock_models").MailTrackingValue} */
        const MailTrackingValue = this.env["mail.tracking.value"];

        const trackingValueIds = [];
        const changedFieldNames = [];
        for (const fname in trackedFieldNamesToField) {
            const initialValue = initialTrackedFieldValues[fname];
            const newValue = record[fname];
            if (!initialValue && !newValue) {
                continue;
            }
            if (initialValue !== newValue) {
                const tracking = MailTrackingValue._create_tracking_values(
                    initialValue,
                    newValue,
                    fname,
                    trackedFieldNamesToField[fname],
                    this
                );
                if (tracking) {
                    trackingValueIds.push(tracking);
                }
                changedFieldNames.push(fname);
            }
        }
        return { changedFieldNames, trackingValueIds };
    }
}
