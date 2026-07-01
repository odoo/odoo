import { useSubEnv } from "@web/owl2/utils";
import { Chatter } from "@mail/chatter/web_portal_project/chatter";

import { props, t } from "@odoo/owl";

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

patch(Chatter.prototype, {
    setup() {
        super.setup(...arguments);
        this.projectSharingProps = props({
            displayFollowButton: t.boolean(),
            isFollower: t.boolean(),
            projectSharingId: t.number().optional(),
        });
        Object.assign(this.state, {
            isFollower: this.projectSharingProps.isFollower,
        });
        this.orm = useService("orm");
        useSubEnv({
            // 'inFrontendPortalChatter' is specific to the frontend portal chatters
            // and should not be set to 'true' in the project sharing chatter environment.
            projectSharingId: this.projectSharingProps.projectSharingId,
        });
    },

    get extraMessageFetchRouteParams() {
        const params = super.extraMessageFetchRouteParams;
        if (this.props.projectSharingId) {
            params.share_only = true;
        }
        return params;
    },

    async toggleIsFollower() {
        this.state.isFollower = await this.orm.call(
            this.thread().model,
            "project_sharing_toggle_is_follower",
            [this.thread().id]
        );
    },
    onPostCallback() {
        super.onPostCallback();
        this.state.isFollower = true;
    },
});
