/** @odoo-module */

import { models } from "@web/../tests/web_test_helpers";

export class Base extends models.ServerModel {
    _name = "base";

    /**
     * Simulates `_mail_track` on `base`
     *
     * @param {string} model
     * @param {Object} trackedFieldNamesToField
     * @param {Object} initialTrackedFieldValues
     * @param {Object} record
     */
    _mailTrack(model, trackedFieldNamesToField, initialTrackedFieldValues, record) {
        const trackingValueIds = [];
        const changedFieldNames = [];
        for (const fname in trackedFieldNamesToField) {
            const initialValue = initialTrackedFieldValues[fname];
            const newValue = record[fname];
            if (initialValue !== newValue) {
                const tracking = this.env["mail.tracking.value"]._createTrackingValues(
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
