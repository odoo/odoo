import { MailActivity } from "@mail/core/common/model_definitions";
import { assignDefined } from "@mail/utils/common/misc";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Activity} */
const MailActivityPatch = {
    setup() {
        super.setup(...arguments);
        this.icon = "fa-tasks";
    },
    serialize() {
        return JSON.parse(JSON.stringify(this.toData(["user_id"])));
    },
};
patch(MailActivity.prototype, MailActivityPatch);
patch(MailActivity, {
    _insert(data, { broadcast = true } = {}) {
        /** @type {import("models").Activity} */
        const activity = this.preinsert(data);
        assignDefined(activity, data);
        if (broadcast) {
            this.store.activityBroadcastChannel?.postMessage({
                type: "INSERT",
                payload: activity.serialize(),
            });
        }
        return activity;
    },
});
export const Activity = MailActivity;
