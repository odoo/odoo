/* @odoo-module */

import { MessagingMenu } from "@mail/core/web/messaging_menu";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(MessagingMenu.prototype, {
    /**
     * @override
     */
    tabToThreadType(tab) {
        const threadTypes = super.tabToThreadType(tab);
        if (tab === "chat" && !this.ui.isSmall) {
            threadTypes.push("livechat");
        }
        if (tab === "livechat") {
            threadTypes.push("livechat");
        }
        return threadTypes;
    },
    /**
     * @override
     */
    get tabs() {
        const items = super.tabs;
        const hasLivechats = Object.values(this.store.Thread.records).some(
            ({ type }) => type === "livechat"
        );
        if (hasLivechats) {
            items.push({
                id: "livechat",
                icon: "fa fa-comments",
                label: _t("Livechat"),
            });
        }
        return items;
    },
});
