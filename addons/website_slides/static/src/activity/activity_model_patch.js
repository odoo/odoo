import { Activity } from "@mail/core/web/activity_model";
import { assignDefined } from "@mail/utils/common/misc";
import { patch } from "@web/core/utils/patch";

/** @type {import("models").Activity} */
const activityPatch = {
    _insert(data, { broadcast = true } = {}) {
        /** @type {import("models").Activity} */
        const activity = super._insert(...arguments);
        if (data.request_partner_id) {
            data.request_partner_id = data.request_partner_id.id;
        }
        assignDefined(activity, data);
        return activity;
    }
};
patch(Activity, activityPatch);
