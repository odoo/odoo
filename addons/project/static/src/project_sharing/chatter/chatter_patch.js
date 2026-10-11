import { Chatter } from "@mail/chatter/web_portal_project/chatter";
import { ProjectSharingRecipientsInput } from "@project/project_sharing/chatter/recipients_input";
import { providePlugins, status, t, useEffect, usePlugin, useProps } from "@odoo/owl";
import { ProjectSharingPlugin } from "@project/project_sharing/chatter/project_sharing_plugin";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

Object.assign(Chatter.components, { ProjectSharingRecipientsInput });

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
        useEffect(() => {
            const recipients = [
                ...(this.thread()?.suggestedRecipients || []),
                ...(this.thread()?.additionalRecipients || []),
            ];
            if (recipients.some((recipient) => recipient.recipient_type === "cc")) {
                this.projectSharingPlugin.showCcField.set(true);
            }
        });
    },

    get extraMessageFetchRouteParams() {
        return super.extraMessageFetchRouteParams;
    },

    async load(thread, requestList) {
        await super.load(thread, requestList);
        if (status(this) === "destroyed") {
            return;
        }
        if (!this.projectSharingPlugin.projectSharingId() || !thread?.id || !this.thread()?.eq(thread)) {
            return;
        }
        const { store_data, recipients_count, default_recipients } = await this.orm.call(
            thread.model,
            "get_project_sharing_chatter_data",
            [[thread.id]]
        );
        if (!store_data || !this.thread()?.eq(thread)) {
            return;
        }
        this.store.insert(store_data);
        thread.recipientsCount = recipients_count;
        const additionalRecipientIds = new Set(
            thread.additionalRecipients.map((recipient) => recipient.partner_id)
        );
        thread.suggestedRecipients = default_recipients
            .filter((recipient) => !additionalRecipientIds.has(recipient.partner_id))
            .map((recipient) => ({
                ...recipient,
                persona: this.store["res.partner"].get(recipient.partner_id),
            }));
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
