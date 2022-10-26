/** @odoo-module **/

import { attr, one } from '@mail/model/model_field';
import { registerModel } from '@mail/model/model_core';

registerModel({
    name: 'MessagingMenuTabView',
    identifyingMode: 'xor',
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
            compute() {
                if (this.ownerAsAll) {
                    return 'all';
                }
                if (this.ownerAsChannel) {
                    return 'channel';
                }
                if (this.ownerAsChat) {
                    return 'chat';
                }
            },
            required: true,
        }),
        isActive: attr({
            compute() {
                return this.messaging.messagingMenu.activeTab === this;
            },
        }),
        name: attr({
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
            required: true,
        }),
        ownerAsAll: one('MessagingMenu', {
            identifying: true,
            inverse: 'allTab',
        }),
        ownerAsChannel: one('MessagingMenu', {
            identifying: true,
            inverse: 'channelTab',
        }),
        ownerAsChat: one('MessagingMenu', {
            identifying: true,
            inverse: 'chatTab',
        }),
    },
});
