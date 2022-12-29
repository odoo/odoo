/** @odoo-module */

import { MessagingMenu } from "@mail/new/web/messaging_menu/messaging_menu";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(MessagingMenu.prototype, "im_livechat", {
    /**
     * @override
     */
    tabToThreadType(tab) {
        const threadTypes = this._super(tab);
        if (tab === "chat") {
            threadTypes.push("livechat");
        }
        return threadTypes;
    },
    /**
     * @override
     */
    get tabs() {
        const items = this._super();
        const hasLivechats = Object.values(this.store.threads).some(
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
