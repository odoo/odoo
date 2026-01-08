/* @odoo-module */

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    /**
     * Simulates `_mail_track` on `base`
     *
     * @param {string} model
     * @param {Object} trackedFieldNamesToField
     * @param {Object} initialTrackedFieldValues
     * @param {Object} record
     * @returns {Object}
     */
    _mockMailBaseModel__MailTrack(
        model,
        trackedFieldNamesToField,
        initialTrackedFieldValues,
        record
    ) {
        const trackingValueIds = [];
        const changedFieldNames = [];
        for (const fname in trackedFieldNamesToField) {
            const initialValue = initialTrackedFieldValues[fname];
            const newValue = record[fname];
            if (initialValue !== newValue) {
                const tracking = this._mockMailTrackingValue_CreateTrackingValues(
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
    },
});
