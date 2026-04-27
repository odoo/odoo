/** @odoo-module */

import { MessagingMenu } from "@mail/core/public_web/messaging_menu";
import { ThreadIcon } from "@mail/core/common/thread_icon";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(MessagingMenu, {
    components: { ...MessagingMenu.components, ThreadIcon },
});

patch(MessagingMenu.prototype, {
    get tabs() {
        const items = super.tabs;
        const hasWhatsApp = Object.values(this.store.Thread.records).some(
            ({ channel_type }) => channel_type === "whatsapp"
        );
        if (hasWhatsApp) {
            items.push({
                icon: "fa fa-whatsapp",
                id: "whatsapp",
                label: _t("WhatsApp"),
            });
        }
        return items;
    },

    get displayStartConversation() {
        return super.displayStartConversation && this.store.discuss.activeTab !== "whatsapp";
    },
});
