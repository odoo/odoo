import { Activity } from "@mail/core/web/activity";

import { patch } from "@web/core/utils/patch";

/** @type {import("@mail/core/web/activity").Activity } */
const ActivityPatch = {
    async onGrantAccess() {
        const activity = this.activity();
        await this.env.services.orm.call(
            "slide.channel",
            "action_grant_access",
            [[activity.res_id]],
            { partner_id: activity.request_partner_id.id }
        );
        activity.remove();
        this.reloadParentView();
    },
    async onRefuseAccess() {
        const activity = this.activity();
        await this.env.services.orm.call(
            "slide.channel",
            "action_refuse_access",
            [[activity.res_id]],
            { partner_id: activity.request_partner_id.id }
        );
        activity.remove();
        this.reloadParentView();
    },
};

patch(Activity.prototype, ActivityPatch);
