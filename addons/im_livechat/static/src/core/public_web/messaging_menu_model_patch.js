import {
    MENU_TABS,
    MessagingMenu,
} from "@mail/core/public_web/messaging_menu/messaging_menu_model";
import { fields } from "@mail/model/export";

import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { patch } from "@web/core/utils/patch";

MENU_TABS.LIVECHAT = "livechat";

/** @type {MessagingMenu} */
const messagingMenuModelPatch = {
    setup() {
        super.setup(...arguments);
        this.livechatTab = fields.One("MessagingMenuTab", {
            compute() {
                if (user.isInternalUser && !user.isRegularUser) {
                    return;
                }
                return {
                    id: MENU_TABS.LIVECHAT,
                    icon: "mode_comment",
                    activeIcon: "mode_comment",
                    label: _t("Live Chats"),
                    sequence: 90,
                    emptyState: {
                        title: _t("No Livechat Session!"),
                        subtitle: _t("Engage with visitors to convert leads or offer services."),
                        action: this.store.env.services.action
                            ? {
                                  text: _t("Connect"),
                                  onClick: () =>
                                      this.store.env.services.action.doAction(
                                          "im_livechat.im_livechat_channel_action"
                                      ),
                              }
                            : undefined,
                    },
                    filters: [
                        {
                            id: "livechat_my",
                            text: _t("My Sessions"),
                            includesChannel: (c) => Boolean(c.self_member_id),
                            isDefault: true,
                        },
                        {
                            id: "livechat_unread",
                            text: _t("Unread"),
                            includesChannel: (c) => c.isUnread,
                        },
                        ...(this.store.has_access_livechat
                            ? [
                                  {
                                      id: "livechat_need_help",
                                      text: _t("Help needed"),
                                      includesChannel: (c) => c.livechat_status === "need_help",
                                  },
                              ]
                            : []),
                    ],
                    actions:
                        this.store.has_access_livechat && this.store.env.services.action
                            ? [
                                  {
                                      id: "livechat_channels",
                                      icon: "add",
                                      text: _t("Channel"),
                                      title: _t("Join or leave live chat channels"),
                                      onClick: () => this.openLivechatChannels(),
                                  },
                              ]
                            : [],
                    includesChannel: (c) =>
                        c.channel_type === "livechat" &&
                        (c.self_member_id?.is_pinned ||
                            c.isLocallyPinned ||
                            c.livechat_status === "need_help"),
                    recordType: "discuss.channel",
                };
            },
        });
    },
    async openLivechatChannels() {
        const actionService = this.store.env.services.action;
        const action = await actionService.loadAction("im_livechat.im_livechat_channel_action");
        actionService.doAction({ ...action, target: "new" });
    },
};
patch(MessagingMenu.prototype, messagingMenuModelPatch);
