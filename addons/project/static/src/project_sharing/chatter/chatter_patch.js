import { Chatter } from "@mail/chatter/web_portal/chatter";

import { useSubEnv } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

patch(Chatter.prototype, {
    setup() {
        super.setup(...arguments);
        Object.assign(this.state, {
            isFollower: this.props.isFollower,
        });
        this.orm = useService("orm");
        useSubEnv({
            projectSharingId: this.props.projectSharingId,
            inFrontendPortalChatter: true,
        });
    },

    async toggleIsFollower() {
        this.state.isFollower = await this.orm.call(
            this.props.threadModel,
            "project_sharing_toggle_is_follower",
            [this.props.threadId]
        );
    },
    onPostCallback() {
        super.onPostCallback();
        this.state.isFollower = true;
    },
});
Chatter.props = [
    ...Chatter.props,
    "token",
    "projectSharingId",
    "isFollower",
    "displayFollowButton",
];
