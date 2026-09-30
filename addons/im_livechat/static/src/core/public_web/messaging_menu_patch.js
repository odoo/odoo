import { MessagingMenu } from "@mail/core/public_web/messaging_menu";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(MessagingMenu.prototype, {
    /**
     * @override
     */
    get _tabs() {
        const items = super._tabs;
        const hasLivechats = Object.values(this.store.Thread.records).some(
            ({ channel_type }) => channel_type === "livechat"
        );
        if (hasLivechats) {
            items.push({
                counter: this.store.discuss.livechats.reduce(
                    (acc, channel) =>
                        channel.self_member_id?.message_unread_counter > 0 ? acc + 1 : acc,
                    0
                ),
                id: "livechat",
                icon: "fa fa-commenting-o",
                activeIcon: "fa fa-commenting",
                label: _t("Live Chats"),
                sequence: 60,
            });
        }
        return items;
    },
});
