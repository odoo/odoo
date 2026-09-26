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
            showCcField: false,
        });
        this.orm = useService("orm");
        providePlugins([ProjectSharingPlugin]);
        this.projectSharingPlugin = usePlugin(ProjectSharingPlugin);
        this.projectSharingPlugin.projectSharingId.set(this.projectSharingProps.projectSharingId);
    },

    get extraMessageFetchRouteParams() {
        return super.extraMessageFetchRouteParams;
    },

    async load() {
        await super.load(...arguments);
        if (this.projectSharingPlugin?.projectSharingId() && this.thread()?.id) {
            const thread = this.thread();
            const { store_data, recipients_count, default_recipients } = await this.orm.call(
                thread.model,
                "get_project_sharing_chatter_data",
                [[thread.id]]
            );
            if (store_data) {
                this.store.insert(store_data);
            }
            thread.recipientsCount = recipients_count ?? thread.recipients?.length ?? 0;
            const existingRecipientIds = new Set(
                (thread.suggestedRecipients || []).map((recipient) => recipient.partner_id)
            );
            const recipients = (default_recipients || []).map((recipient) => ({
                ...recipient,
                persona: recipient.partner_id
                    ? this.store["res.partner"].insert({
                          id: recipient.partner_id,
                          name: recipient.name,
                          email: recipient.email,
                      })
                    : undefined,
            }));
            thread.suggestedRecipients = [
                ...(thread.suggestedRecipients || []),
                ...recipients.filter(
                    (recipient) => !existingRecipientIds.has(recipient.partner_id)
                ),
            ];
        }
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
