import { openChannelInvitationDialog } from "../common/channel_invitation";
import {
    MENU_TABS,
    MessagingMenu,
} from "@mail/core/public_web/messaging_menu/messaging_menu_model";
import { MessagingMenuEmptyChannel } from "@mail/discuss/core/public_web/messaging_menu_empty_channel";
import { compareChannels, compareMeetings } from "@mail/discuss/core/public_web/meeting_compare";
import { fields } from "@mail/model/export";
import { markup } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

MENU_TABS.CHAT = "chat";
MENU_TABS.CHANNEL = "channel";
MENU_TABS.MEETING = "meeting";

/** @type {import("models").MessagingMenu} */
const messagingMenuPatch = {
    setup() {
        super.setup(...arguments);
        this.chatTab = fields.One("MessagingMenuTab", {
            compute() {
                return {
                    id: MENU_TABS.CHAT,
                    recordType: "discuss.channel",
                    includesChannel: (c) =>
                        c.self_member_id?.is_pinned &&
                        ["chat", "group"].includes(c.channel_type) &&
                        !c.isMeetingOrMeetingChild,
                    icon: "group",
                    iconClass: "oi-filled",
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
                            includesChannel: (c) => c.isUnread,
                        },
                        {
                            id: "chat_group",
                            text: _t("Group"),
                            includesChannel: (c) => c.channel_type === "group",
                        },
                    ],
                    actions:
                        this.store.self_user?.share === false
                            ? [
                                  {
                                      id: "new_chat",
                                      icon: "add",
                                      text: _t("Chat"),
                                      onClick: () => openChannelInvitationDialog(this.store.env),
                                  },
                              ]
                            : [],
                };
            },
            eager: true,
        });
        this.channelTab = fields.One("MessagingMenuTab", {
            compute() {
                return {
                    id: MENU_TABS.CHANNEL,
                    recordType: "discuss.channel",
                    includesChannel: (c) =>
                        c.channel_type === "channel" &&
                        Boolean(
                            c.isLocallyPinned || c.self_member_id?.is_pinned || c.needactionCounter
                        ),
                    icon: "tag",
                    sequence: 30,
                    label: _t("Channels"),
                    emptyState: {
                        title: _t("Stay updated on your favourite topics"),
                        subtitle: _t("Find channels to follow below"),
                        component: MessagingMenuEmptyChannel,
                    },
                    filters: [
                        {
                            id: "channel_unread",
                            text: _t("Unread"),
                            includesChannel: (c) => c.isUnread,
                        },
                        {
                            id: "channel_thread",
                            text: _t("Thread"),
                            includesChannel: (c) => Boolean(c.parent_channel_id),
                        },
                    ],
                    actions:
                        this.store.self_user?.share === false
                            ? [
                                  {
                                      id: "new_channel",
                                      text: _t("Channel"),
                                      icon: "add",
                                      title: _t("New channel"),
                                      onClick: () =>
                                          this.store.env.services.action.doAction(
                                              "mail.discuss_channel_action"
                                          ),
                                  },
                              ]
                            : [],
                };
            },
            eager: true,
        });
        this.meetingTab = fields.One("MessagingMenuTab", {
            compute() {
                return {
                    id: MENU_TABS.MEETING,
                    recordType: "discuss.channel",
                    includesChannel: (c) =>
                        c.channel_type === "group" &&
                        c.self_member_id?.is_pinned &&
                        c.isMeetingOrMeetingChild,
                    compareChannels: compareMeetings,
                    icon: "videocam",
                    iconClass: "oi-filled",
                    sequence: 45,
                    label: _t("Meetings"),
                    emptyState: {
                        title: _t("No video conference planned!"),
                        subtitle: markup`${_t(
                            "Collaborate with coworkers and customers in video calls."
                        )}<br/>${_t("No install needed.")}`,
                    },
                    filters: [
                        {
                            id: "meeting_today",
                            text: _t("Today"),
                            includesChannel: (c) => c.has_meeting_today,
                            isDefault: true,
                            sequence: 10,
                        },
                        {
                            id: "meeting_unread",
                            text: _t("Unread"),
                            compareChannels,
                            includesChannel: (c) => c.isUnread,
                            sequence: 20,
                        },
                        {
                            id: "meeting_thread",
                            text: _t("Thread"),
                            compareChannels,
                            includesChannel: (c) => Boolean(c.parent_channel_id),
                            sequence: 30,
                        },
                    ],
                    actions:
                        this.store.self_user?.share === false
                            ? [
                                  {
                                      id: "start_meeting",
                                      icon: "video_call",
                                      iconClass: "oi-filled",
                                      text: _t("Meeting"),
                                      title: _t("New Meeting"),
                                      subActions: [
                                          {
                                              id: "start_now",
                                              text: _t("Start Now"),
                                              onClick: () => this.store.requestStartMeeting(),
                                          },
                                          ...this.extraTabActions(MENU_TABS.MEETING),
                                      ],
                                  },
                              ]
                            : [],
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
            counter -= this["discuss.channel"].records
                .values()
                .reduce((acc, channel) => acc + channel.message_needaction_counter, 0);
        }
        return counter;
    },
    /** @override */
    get odooBotNotificationsTab() {
        return this.chatTab;
    },
    /** @override */
    notificationMatchesExtra(message) {
        return (
            super.notificationMatchesExtra(message) && message.thread?.model !== "discuss.channel"
        );
    },
};
patch(MessagingMenu.prototype, messagingMenuPatch);
