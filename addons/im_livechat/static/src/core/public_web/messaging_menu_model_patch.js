import { MessagingMenu } from "@mail/core/public_web/messaging_menu/messaging_menu_model";
import { fields } from "@mail/model/export";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

/** @type {MessagingMenu} */
const messagingMenuPatch = {
    setup() {
        super.setup(...arguments);
        this.livechatTab = fields.One("MessagingMenuTab", {
            compute() {
                return {
                    id: "livechat",
                    icon: "fa fa-commenting-o",
                    activeIcon: "fa fa-commenting",
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
                    filters: this.store.has_access_livechat
                        ? [
                              {
                                  id: "livechat_need_help",
                                  text: _t("Help needed"),
                                  domain: [["livechat_status", "=", "need_help"]],
                                  matchesChannel: (c) => c.livechat_status === "need_help",
                              },
                          ]
                        : [],
                    domain: [
                        ["channel_type", "=", "livechat"],
                        "|",
                        ["self_member_id.is_pinned", "=", true],
                        ["livechat_status", "=", "need_help"],
                    ],
                    priorityDomain: [["self_member_id.is_pinned", "=", true]],
                    recordType: "discuss.channel",
                    matchesChannel: (c) =>
                        c.channel_type === "livechat" &&
                        (c.self_member_id?.is_pinned ||
                            c.isLocallyPinned ||
                            c.livechat_status === "need_help"),
                };
            },
            eager: true,
        });
    },
};
patch(MessagingMenu.prototype, messagingMenuPatch);
