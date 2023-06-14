/** @odoo-module **/

import { Activity } from "@mail/core/web/activity";
import { deleteActivity } from "@mail/core/web/activity_service";

import { patch } from "@web/core/utils/patch";

/** @type {import("@mail/core/web/activity").Activity } */
const ActivityPatch = {
    async onGrantAccess() {
        await this.env.services.orm.call(
            "slide.channel",
            "action_grant_access",
            [[this.props.data.res_id]],
            { partner_id: this.props.data.request_partner_id }
        );
        deleteActivity(this.props.data);
        this.props.reloadParentView();
    },
    async onRefuseAccess() {
        await this.env.services.orm.call(
            "slide.channel",
            "action_refuse_access",
            [[this.props.data.res_id]],
            { partner_id: this.props.data.request_partner_id }
        );
        deleteActivity(this.props.data);
        this.props.reloadParentView();
    },
};

patch(Activity.prototype, "website_slides", ActivityPatch);
