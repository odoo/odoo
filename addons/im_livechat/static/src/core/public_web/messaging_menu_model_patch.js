import {
    MENU_TABS,
    MessagingMenu,
} from "@mail/core/public_web/messaging_menu/messaging_menu_model";
import { fields } from "@mail/model/export";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

MENU_TABS.LIVECHAT = "livechat";

/** @type {MessagingMenu} */
const messagingMenuModelPatch = {
    setup() {
        super.setup(...arguments);
        this.livechatTab = fields.One("MessagingMenuTab");
        this.assignComputed("livechatTab", function computeLivechatTab() {
            return this.store.MessagingMenuTab.insert({
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
                includesChannel: (c) =>
                    c.channel_type === "livechat" &&
                    (c.self_member_id?.is_pinned ||
                        c.isLocallyPinned ||
                        c.livechat_status === "need_help"),
                recordType: "discuss.channel",
            });
        });
    },
};
patch(MessagingMenu.prototype, messagingMenuModelPatch);
