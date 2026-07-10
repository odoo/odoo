import { Discuss } from "@mail/core/public_web/discuss_app/discuss_app";
import { DiscussInvitationDialog } from "@mail/core/public_web/discuss_app/discuss_invitation_dialog";
import { propComputed, useOnChange } from "@mail/utils/common/hooks";

import { Component, onMounted, onWillUnmount, t } from "@odoo/owl";

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { router } from "@web/core/browser/router";

export class DiscussClientAction extends Component {
    static components = { Discuss };
    static template = "mail.DiscussClientAction";

    setup() {
        super.setup();
        this.action = propComputed(
            "action",
            t
                .object({
                    context: t.object({
                        active_id: t.or([t.string(), t.number()]).optional(),
                    }),
                    params: t
                        .object({
                            active_id: t.or([t.string(), t.number()]).optional(),
                            default_active_id: t.or([t.string(), t.number()]).optional(),
                            highlight_message_id: t.number().optional(),
                            invitation_token: t.string().optional(),
                        })
                        .optional(),
                })
                // The public page doesn't use the action service, but overrides
                // `getActiveId` to provide the id from the URL instead of the action.
                .optional()
        );
        this.store = useService("mail.store");
        useOnChange(
            () => [this.action()],
            (action) => this.restoreDiscussThread(action)
        );
        onMounted(() => (this.store.discuss.isActive = true));
        onWillUnmount(() => (this.store.discuss.isActive = false));
    }

    getActiveId(action) {
        return (
            action.context.active_id ??
            action.params?.active_id ??
            this.store["mail.thread"].localIdToActiveId(this.store.discuss.thread?.localId) ??
            (this.env.services.ui.isSmall ? undefined : this.store.discuss.lastActiveId)
        );
    }

    /** @param {string} [rawActiveId] */
    parseActiveId(rawActiveId) {
        if (!rawActiveId) {
            return undefined;
        }
        const [model, id] = rawActiveId.split("_");
        return [model, parseInt(id)];
    }

    /**
     * Restore the discuss thread according to the active_id in the action if
     * necessary.
     *
     * @param {Object} action
     */
    async restoreDiscussThread(action) {
        const rawActiveId = this.getActiveId(action);
        const parsedActiveId = this.parseActiveId(rawActiveId);
        if (!parsedActiveId) {
            await this.store.isReadyPromise;
            this.store.discuss.thread = undefined;
            this.store.discuss.hasRestoredThread = true;
            const odoobotChat = this.store.odoobot?.searchChat();
            const selfMember = odoobotChat?.self_member_id;
            if (odoobotChat && selfMember?.is_pinned && !selfMember.seen_message_id) {
                odoobotChat.setAsDiscussThread(false);
            }
            return;
        }
        const [model, id] = parsedActiveId;
        if (model === "discuss.tab") {
            await this.store.isReadyPromise;
            this.store.discuss.thread = undefined;
            const tab = this.store.messagingMenu.allTabs.find((t) => t.id === id);
            if (tab) {
                this.store.discuss.sidebarState.activeTab = tab;
            }
            this.store.discuss.hasRestoredThread = true;
            return;
        }
        let activeThread;
        let invitedChannel;
        if (
            action?.params?.invitation_token &&
            model === "discuss.channel" &&
            this.store.self_user
        ) {
            await this.store.isReadyPromise;
            const result = await this.store.fetchStoreData(
                "/discuss/channel/invitation",
                {
                    channel_id: id,
                    invitation_token: action.params.invitation_token,
                },
                {
                    requestData: true,
                }
            );
            invitedChannel = result.channel;
            if (!invitedChannel || !invitedChannel.self_member_id) {
                this.store.discuss.thread = undefined;
            } else {
                activeThread = await this.store["mail.thread"].getOrFetch({ model, id });
            }
        } else {
            activeThread = await this.store["mail.thread"].getOrFetch({ model, id });
        }
        if (activeThread && !activeThread.discussAppAsThread) {
            const highlight_message_id =
                action?.params?.highlight_message_id || router.current.highlight_message_id;
            if (highlight_message_id) {
                activeThread.highlightMessage = highlight_message_id;
                delete action?.params?.highlight_message_id;
                delete router.current?.highlight_message_id;
            }
            activeThread.setAsDiscussThread(false);
        }
        this.store.discuss.hasRestoredThread = true;
        if (invitedChannel) {
            await new Promise((resolve) =>
                this.store.env.services.dialog.add(DiscussInvitationDialog, {
                    channel: invitedChannel,
                    onConfirm: async () => {
                        await this.store.fetchStoreData("/discuss/channel/add_members", {
                            channel_id: id,
                            user_ids: [this.store.self_user.id],
                            invitation_token: action.params.invitation_token,
                        });
                        // refresh the channel to get the updated rtc_session_ids
                        await this.store.rtc.constructor.pingChannel(invitedChannel);
                        const thread = await this.store["mail.thread"].getOrFetch({ model, id });
                        if (thread) {
                            thread.setAsDiscussThread(false);
                        }
                        if (
                            invitedChannel.rtc_session_ids &&
                            invitedChannel.rtc_session_ids
                                .map((rtcSession) => rtcSession.channel_member_id)
                                .filter((memberId) => !!memberId).length > 0
                        ) {
                            await this.store.rtc.toggleCall(invitedChannel);
                        }
                    },
                    close: () => {
                        delete action.params.invitation_token;
                        resolve();
                    },
                })
            );
        }
    }
}

registry.category("actions").add("mail.action_discuss", DiscussClientAction);
