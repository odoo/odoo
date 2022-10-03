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
            this.messaging.messagingMenu.update({ activeTabId: this.tabId });
        },
    },
    fields: {
        isActiveTab: attr({
            compute() {
                return this.messaging.messagingMenu.activeTab === this;
            },
        }),
        ownerAsAllTab: one('MessagingMenu', {
            identifying: true,
            inverse: 'allTab',
        }),
        ownerAsChannelTab: one('MessagingMenu', {
            identifying: true,
            inverse: 'channelTab',
        }),
        ownerAsChatTab: one('MessagingMenu', {
            identifying: true,
            inverse: 'chatTab',
        }),
        /**
         * Note: when possible, better use the relations with MessagingMenu
         * rather than these hardcoded IDs.
         */
        tabId: attr({
            compute() {
                if (this.ownerAsAllTab) {
                    return 'all';
                }
                if (this.ownerAsChannelTab) {
                    return 'channel';
                }
                if (this.ownerAsChatTab) {
                    return 'chat';
                }
            },
            required: true,
        }),
        tabName: attr({
            compute() {
                if (this.ownerAsAllTab) {
                    return this.env._t("All");
                }
                if (this.ownerAsChannelTab) {
                    return this.env._t("Channels");
                }
                if (this.ownerAsChatTab) {
                    return this.env._t("Chats");
                }
            },
            required: true,
        }),
    },
});
