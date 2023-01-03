/** @odoo-module **/

import { attr, one, Model } from "@mail/model";

Model({
    name: "MessagingMenuTabView",
    template: "mail.MessagingMenuTabView",
    identifyingMode: "xor",
    recordMethods: {
        /**
         * @param {MouseEvent} ev
         */
        onClick(ev) {
            this.messaging.messagingMenu.update({ activeTabId: this.id });
        },
    },
    fields: {
        /**
         * Note: when possible, better use the relations with MessagingMenu
         * rather than these hardcoded IDs.
         */
        id: attr({
            required: true,
            compute() {
                if (this.ownerAsAll) {
                    return "all";
                }
                if (this.ownerAsChannel) {
                    return "channel";
                }
                if (this.ownerAsChat) {
                    return "chat";
                }
            },
        }),
        isActive: attr({
            compute() {
                return this.messaging.messagingMenu.activeTab === this;
            },
        }),
        name: attr({
            required: true,
            compute() {
                if (this.ownerAsAll) {
                    return this.env._t("All");
                }
                if (this.ownerAsChannel) {
                    return this.env._t("Channels");
                }
                if (this.ownerAsChat) {
                    return this.env._t("Chats");
                }
            },
        }),
        ownerAsAll: one("MessagingMenu", { identifying: true, inverse: "allTab" }),
        ownerAsChannel: one("MessagingMenu", { identifying: true, inverse: "channelTab" }),
        ownerAsChat: one("MessagingMenu", { identifying: true, inverse: "chatTab" }),
    },
});
