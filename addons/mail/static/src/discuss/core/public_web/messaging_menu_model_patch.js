import { openChannelInvitationDialog } from "../common/channel_invitation";
import { MessagingMenu } from "@mail/core/public_web/messaging_menu/messaging_menu_model";
import { MessagingMenuEmptyChannel } from "@mail/discuss/core/public_web/messaging_menu_empty_channel";
import { fields } from "@mail/model/export";
import { markup } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(MessagingMenu.prototype, {
    setup() {
        super.setup(...arguments);
        this.chatTab = fields.One("MessagingMenuTab", {
            compute() {
                return {
                    id: "chat",
                    recordType: "discuss.channel",
                    domain: [
                        ["channel_type", "in", ["chat", "group"]],
                        ["default_display_mode", "!=", "video_full_screen"],
                        ["self_member_id.is_pinned", "=", true],
                    ],
                    icon: "oi oi-users",
                    sequence: 15,
                    label: _t("Chats"),
                    emptyState: {
                        title: _t("No messages yet!"),
                        subtitle: _t("Chat with your coworkers on desktop or on mobile."),
                    },
                    filters: [
                        {
                            id: "chat_unread",
                            text: _t("Unread"),
                            domain: [["self_member_id.is_unread", "=", true]],
                            matchesChannel: (c) =>
                                Boolean(c.importantCounter ?? c.needactionCounter),
                        },
                    ],
                    actions:
                        this.store.self_user?.share === false
                            ? [
                                  {
                                      id: "new_chat",
                                      icon: "fa fa-plus",
                                      text: _t("Chat"),
                                      onClick: () => openChannelInvitationDialog(this.store.env),
                                  },
                              ]
                            : [],
                    matchesChannel: (c) =>
                        c.self_member_id?.is_pinned &&
                        ["chat", "group"].includes(c.channel_type) &&
                        c.default_display_mode !== "video_full_screen",
                };
            },
            eager: true,
        });
        this.channelTab = fields.One("MessagingMenuTab", {
            compute() {
                const pinned = ["self_member_id.is_pinned", "=", true];
                const domain = [
                    ["channel_type", "=", "channel"],
                    ...(this.store.self_user?.share === false
                        ? ["|", pinned, ["message_needaction", "=", true]]
                        : [pinned]),
                ];
                return {
                    id: "channel",
                    recordType: "discuss.channel",
                    domain,
                    icon: "fa fa-hashtag",
                    sequence: 30,
                    label: _t("Channels"),
                    emptyState: {
                        title: _t("Stay updated on your favourite topics"),
                        subtitle: _t("Find channels to follow below"),
                        component: MessagingMenuEmptyChannel,
                    },
                    actions:
                        this.store.self_user?.share === false
                            ? [
                                  {
                                      id: "new_channel",
                                      text: _t("Channel"),
                                      icon: "fa fa-plus",
                                      title: _t("New channel"),
                                      onClick: () =>
                                          this.store.env.services.action.doAction(
                                              "mail.discuss_channel_action"
                                          ),
                                  },
                              ]
                            : [],
                    matchesChannel: (c) =>
                        c.channel_type === "channel" &&
                        Boolean(
                            c.isLocallyPinned || c.self_member_id?.is_pinned || c.needactionCounter
                        ),
                };
            },
            eager: true,
        });
        this.meetingTab = fields.One("MessagingMenuTab", {
            compute() {
                return {
                    id: "meeting",
                    recordType: "discuss.channel",
                    domain: [
                        ["channel_type", "=", "group"],
                        ["default_display_mode", "=", "video_full_screen"],
                        ["self_member_id.is_pinned", "=", true],
                    ],
                    icon: "fa fa-video-camera",
                    sequence: 45,
                    label: _t("Meetings"),
                    emptyState: {
                        title: _t("No video conference planned!"),
                        subtitle: markup`${_t(
                            "Collaborate with coworkers and customers in video calls."
                        )}<br/>${_t("No install needed.")}`,
                    },
                    actions:
                        this.store.self_user?.share === false
                            ? [
                                  {
                                      id: "start_meeting",
                                      icon: { template: "mail.NewMeetingIcon" },
                                      text: _t("Meeting"),
                                      onClick: () => this.store.startMeeting(),
                                  },
                              ]
                            : [],
                    matchesChannel: (c) =>
                        c.channel_type === "group" &&
                        c.self_member_id?.is_pinned &&
                        c.default_display_mode === "video_full_screen",
                };
            },
            eager: true,
        });
    },
    /** @override */
    _computeGlobalCounter() {
        let counter = super._computeGlobalCounter();
        // Discuss channel model can be missing when initializing the store (dummy store).
        if (this.notificationTab && this["discuss.channel"]) {
            // Needactions are counted in the notification tab, but we discard them for channels
            // so that there is only +1 per channel.
            counter -= Object.values(this["discuss.channel"].records).reduce(
                (acc, channel) => acc + channel.message_needaction_counter,
                0
            );
        }
        return counter;
    },
    /** @override */
    get odooBotNotificationsTab() {
        return this.chatTab;
    },
    /** @override */
    get notificationExtraDomain() {
        return [...super.notificationExtraDomain, ["model", "!=", "discuss.channel"]];
    },
    /** @override */
    notificationMatchesExtra(message) {
        return (
            super.notificationMatchesExtra(message) && message.thread?.model !== "discuss.channel"
        );
    },
});
