/** @odoo-module */

import { models } from "@web/../tests/web_test_helpers";

export class Base extends models.ServerModel {
    _name = "base";

    /**
     * @param {string} model
     * @param {Object} trackedFieldNamesToField
     * @param {Object} initialTrackedFieldValues
     * @param {Object} record
     */
    _mail_track(model, trackedFieldNamesToField, initialTrackedFieldValues, record) {
        /** @type {import("mock_models").MailTrackingValue} */
        const MailTrackingValue = this.env["mail.tracking.value"];

        const trackingValueIds = [];
        const changedFieldNames = [];
        for (const fname in trackedFieldNamesToField) {
            const initialValue = initialTrackedFieldValues[fname];
            const newValue = record[fname];
            if (initialValue !== newValue) {
                const tracking = MailTrackingValue._create_tracking_values(
                    initialValue,
                    newValue,
                    fname,
                    trackedFieldNamesToField[fname],
                    model
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
