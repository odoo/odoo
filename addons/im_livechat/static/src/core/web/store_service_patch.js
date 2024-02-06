/* @odoo-module */

import { Store } from "@mail/core/common/store_service";
import { _t } from "@web/core/l10n/translation";

import { patch } from "@web/core/utils/patch";

patch(Store.prototype, {
    /**
     * @override
     */
    onStarted() {
        super.onStarted(...arguments);
        this.fetchData({ get_livechat_channels: true }).then(() => {
            this.DiscussAppCategory.insert(
                Object.values(this.LivechatChannel.records).map((channel) => ({
                    id: `im_livechat.channel_${channel.id}`,
                    name: channel.name,
                    livechatChannel: channel,
                    sequence: 100 + channel.id,
                    joinTitle: _t("Join %s", channel.name),
                    leaveTitle: _t("Leave %s", channel.name),
                }))
            );
        });
    },
    /**
     * @override
     */
    tabToThreadType(tab) {
        const threadTypes = super.tabToThreadType(tab);
        if (tab === "chat" && !this.env.services.ui.isSmall) {
            threadTypes.push("livechat");
        }
        if (tab === "livechat") {
            threadTypes.push("livechat");
        }
        return threadTypes;
    },
});
