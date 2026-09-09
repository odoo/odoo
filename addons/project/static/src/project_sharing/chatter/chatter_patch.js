import { Chatter } from "@mail/chatter/web_portal_project/chatter";
import { RecipientsInput } from "@mail/core/web/recipients_input";
import { providePlugins, t, usePlugin, useProps } from "@odoo/owl";
import { ProjectSharingPlugin } from "@project/project_sharing/chatter/project_sharing_plugin";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

Object.assign(Chatter.components, { RecipientsInput });

patch(Chatter.prototype, {
    setup() {
        super.setup(...arguments);
        this.projectSharingProps = useProps({
            displayFollowButton: t.boolean(),
            isFollower: t.boolean(),
            projectSharingId: t.number().optional(),
        });
        Object.assign(this.state, {
            isFollower: this.projectSharingProps.isFollower,
        });
        this.orm = useService("orm");
        providePlugins([ProjectSharingPlugin]);
        this.projectSharingPlugin = usePlugin(ProjectSharingPlugin);
        this.projectSharingPlugin.projectSharingId.set(this.projectSharingProps.projectSharingId);
    },

    get extraMessageFetchRouteParams() {
        return super.extraMessageFetchRouteParams;
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
