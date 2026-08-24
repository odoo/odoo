import { Chatter } from "@mail/chatter/web_portal_project/chatter";
import { providePlugins, t, usePlugin, useProps } from "@odoo/owl";
import { ProjectSharingPlugin } from "@project/project_sharing/chatter/project_sharing_plugin";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

patch(Chatter.prototype, {
    setup() {
        super.setup(...arguments);
        this.projectSharingProps = useProps({
            displayFollowButton: t.boolean(),
            isFollower: t.boolean(),
            projectSharingId: t.number().optional(),
        });
        this.orm = useService("orm");
        providePlugins([ProjectSharingPlugin]);
        this.projectSharingPlugin = usePlugin(ProjectSharingPlugin);
        this.projectSharingPlugin.isFollower.set(this.projectSharingProps.isFollower);
        this.projectSharingPlugin.projectSharingId.set(this.projectSharingProps.projectSharingId);
    },

    get extraMessageFetchRouteParams() {
        return super.extraMessageFetchRouteParams;
    },

    async toggleIsFollower() {
        this.projectSharingPlugin.isFollower.set(
            await this.orm.call(this.state.thread().model, "project_sharing_toggle_is_follower", [
                this.state.thread().id,
            ])
        );
    },
    onPostCallback() {
        super.onPostCallback();
        this.projectSharingPlugin.isFollower.set(true);
    },
});
