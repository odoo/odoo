import { Activity } from "@mail/core/web/activity";

import { patch } from "@web/core/utils/patch";

/** @type {import("@mail/core/web/activity").Activity } */
const ActivityPatch = {
    async onGrantAccess() {
        await this.env.services.orm.call(
            "slide.channel",
            "action_grant_access",
            [[this.props.activity.res_id]],
            { partner_id: this.props.activity.request_partner_id.id }
        );
        this.props.activity.remove();
        this.props.reloadParentView();
    },
    async onRefuseAccess() {
        await this.env.services.orm.call(
            "slide.channel",
            "action_refuse_access",
            [[this.props.activity.res_id]],
            { partner_id: this.props.activity.request_partner_id.id }
        );
        this.props.activity.remove();
        this.props.reloadParentView();
    },
};

patch(Activity.prototype, ActivityPatch);
